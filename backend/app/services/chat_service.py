import logging
import uuid
import json
import asyncio
from typing import AsyncGenerator, List, Dict
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from google import genai
from google.genai import types

from app.core.config import settings
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.chat import ChatRequest
from app.db.session import AsyncSessionLocal
from app.services.coordinator_service import coordinator_service

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None

    async def _get_or_create_conversation(self, user: User, conversation_id: uuid.UUID | None) -> Conversation:
        """Fetch existing conversation or create a new one in the DB."""
        async with AsyncSessionLocal() as db:
            if conversation_id:
                stmt = select(Conversation).options(selectinload(Conversation.messages)).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user.id
                )
                result = await db.execute(stmt)
                conv = result.scalars().first()
                if conv:
                    return conv
                    
            # Create new if none exists or none provided
            conv = Conversation(user_id=user.id)
            db.add(conv)
            await db.commit()
            
            # Re-fetch with selectinload to initialize relationships
            stmt = select(Conversation).options(selectinload(Conversation.messages)).where(
                Conversation.id == conv.id
            )
            result = await db.execute(stmt)
            return result.scalars().first()

    async def _save_messages(self, conversation_id: uuid.UUID, user_message: str, ai_message: str):
        """Save the interaction to the database securely."""
        async with AsyncSessionLocal() as db:
            msg_user = Message(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                model="user"
            )
            msg_ai = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=ai_message,
                model="gemini-2.5-flash"
            )
            db.add_all([msg_user, msg_ai])
            await db.commit()

    async def _generate_title(self, conversation_id: uuid.UUID, first_message: str):
        """Background task to generate a title for new conversations."""
        if not self.client:
            return
            
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Generate a very short 3-5 word title for a conversation that starts with this message: '{first_message}'",
                config=types.GenerateContentConfig(temperature=0.3)
            )
            title = response.text.strip().strip('"\'')
            
            async with AsyncSessionLocal() as db:
                stmt = select(Conversation).where(Conversation.id == conversation_id)
                result = await db.execute(stmt)
                conv = result.scalars().first()
                if conv:
                    conv.title = title
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")

    def _get_gemini_tools(self) -> list[types.Tool]:
        """Convert MCP Registry tools into Gemini Tools."""
        from app.services.mcp_registry import mcp_registry
        mcp_tools = mcp_registry.get_all_tools()
        
        declarations = []
        for t in mcp_tools:
            properties = {}
            required = []
            for p in t.parameters:
                type_map = {
                    "string": types.Type.STRING,
                    "integer": types.Type.INTEGER,
                    "boolean": types.Type.BOOLEAN,
                    "number": types.Type.NUMBER,
                    "array": types.Type.ARRAY,
                    "object": types.Type.OBJECT
                }
                gemini_type = type_map.get(p.type, types.Type.STRING)
                properties[p.name] = types.Schema(type=gemini_type, description=p.description)
                if p.required:
                    required.append(p.name)
                    
            decl = types.FunctionDeclaration(
                name=t.name.replace(".", "_"),
                description=t.description,
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=properties,
                    required=required if required else None
                ) if properties else None
            )
            declarations.append(decl)
            
        if not declarations:
            return None
        return [types.Tool(function_declarations=declarations)]

    async def chat_stream(self, request: ChatRequest, user: User) -> AsyncGenerator[str, None]:
        if not self.client:
            yield f"data: {json.dumps({'error': 'Gemini API Key missing'})}\n\n"
            return

        conv = await self._get_or_create_conversation(user, request.conversation_id)
        
        system_instruction = (
            "You are Nexus AI, a helpful, intelligent assistant. "
            "You have access to backend tools to search files, memory, github, etc. "
            "Always use the appropriate tools to answer user questions when possible. "
            "You must format all your responses in standard Markdown. "
            "Be concise, clear, and highly capable."
        )

        contents = []
        for msg in conv.messages:
            contents.append(types.Content(role="model" if msg.role == "assistant" else "user", parts=[types.Part.from_text(text=msg.content)]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=request.message)]))

        gemini_tools = self._get_gemini_tools()
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=gemini_tools,
            temperature=0.2
        )

        ai_full_response = ""
        
        try:
            meta = json.dumps({"conversation_id": str(conv.id), "event": "start"})
            yield f"data: {meta}\n\n"
            
            response_stream = self.client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=contents,
                config=config
            )
            
            function_calls = []
            model_content_parts = []
            
            for chunk in response_stream:
                if chunk.text:
                    ai_full_response += chunk.text
                    model_content_parts.append(types.Part.from_text(text=chunk.text))
                    payload = json.dumps({"chunk": chunk.text, "conversation_id": str(conv.id)})
                    yield f"data: {payload}\n\n"
                if chunk.function_calls:
                    function_calls.extend(chunk.function_calls)
                    for fc in chunk.function_calls:
                        model_content_parts.append(types.Part.from_function_call(name=fc.name, args=fc.args))
                    
            if function_calls:
                yield f"data: {json.dumps({'chunk': '\n*Executing tools...*\n', 'conversation_id': str(conv.id)})}\n\n"
                
                from app.services.mcp_registry import mcp_registry
                from app.schemas.mcp import ToolExecuteRequest
                
                function_responses = []
                for fc in function_calls:
                    tool_name = fc.name.replace("_", ".")
                    execute_req = ToolExecuteRequest(tool_name=tool_name, arguments=fc.args or {})
                    res = await mcp_registry.execute_tool(execute_req, current_user=user)
                    
                    function_responses.append(types.Part.from_function_response(
                        name=fc.name,
                        response={"result": res.result if res.success else res.error}
                    ))
                
                # Append the model's function calls to history
                contents.append(types.Content(role="model", parts=model_content_parts))
                # Append the function responses to history
                contents.append(types.Content(role="user", parts=function_responses))
                
                # Generate final response based on tool results
                final_stream = self.client.models.generate_content_stream(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_instruction)
                )
                
                for chunk in final_stream:
                    if chunk.text:
                        ai_full_response += chunk.text
                        payload = json.dumps({"chunk": chunk.text, "conversation_id": str(conv.id)})
                        yield f"data: {payload}\n\n"

            yield f"data: {json.dumps({'event': 'end'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
        finally:
            if ai_full_response:
                asyncio.create_task(self._save_messages(conv.id, request.message, ai_full_response))
            if not conv.title and len(conv.messages) == 0:
                asyncio.create_task(self._generate_title(conv.id, request.message))

# Singleton
chat_service = ChatService()
