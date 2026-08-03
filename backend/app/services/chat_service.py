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
            await db.refresh(conv)
            
            # Need to initialize messages since it's fresh
            conv.messages = []
            return conv

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

    async def chat_stream(self, request: ChatRequest, user: User) -> AsyncGenerator[str, None]:
        """
        The main chat entry point. It yields Server-Sent Events (SSE).
        It checks if the request requires the Agent Coordinator, or just standard chat.
        For simplicity, if we want agents, we can route it through the coordinator.
        But the requirement is to 'Return markdown, streaming responses'.
        Since the coordinator isn't natively streaming yet, we will stream the standard LLM response here,
        and if it's a complex task, we could trigger the coordinator.
        For now, this handles pure streaming LLM with context.
        """
        if not self.client:
            yield f"data: {json.dumps({'error': 'Gemini API Key missing'})}\n\n"
            return

        # Fetch or create conversation history
        conv = await self._get_or_create_conversation(user, request.conversation_id)
        
        # Build prompt context
        history = []
        for msg in conv.messages:
            history.append(f"{msg.role}: {msg.content}")
            
        history_text = "\n".join(history)
        
        system_instruction = (
            "You are Nexus AI, a helpful, intelligent assistant. "
            "You must format all your responses in standard Markdown. "
            "Be concise, clear, and highly capable."
        )
        
        prompt = f"Chat History:\n{history_text}\n\nUser: {request.message}\nAssistant:"

        ai_full_response = ""
        
        try:
            # Yield initial metadata (so frontend gets conversation ID immediately)
            meta = json.dumps({"conversation_id": str(conv.id), "event": "start"})
            yield f"data: {meta}\n\n"
            
            response_stream = self.client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            
            for chunk in response_stream:
                if chunk.text:
                    ai_full_response += chunk.text
                    # Server-Sent Event format
                    payload = json.dumps({"chunk": chunk.text, "conversation_id": str(conv.id)})
                    yield f"data: {payload}\n\n"
                    
            # Yield end event
            yield f"data: {json.dumps({'event': 'end'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
        finally:
            # Save the interaction to DB once stream finishes or breaks
            if ai_full_response:
                # Spawn a background task so it doesn't block closing the generator
                asyncio.create_task(self._save_messages(conv.id, request.message, ai_full_response))
            
            # Generate title if it's a brand new conversation
            if not conv.title and len(conv.messages) == 0:
                asyncio.create_task(self._generate_title(conv.id, request.message))

# Singleton
chat_service = ChatService()
