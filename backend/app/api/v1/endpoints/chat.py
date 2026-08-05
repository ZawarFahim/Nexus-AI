from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Any
import uuid
from sqlalchemy import select

from app.api import deps
from app.schemas.chat import ChatRequest, ConversationSchema, MessageSchema
from app.services.chat_service import chat_service
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.db.session import AsyncSessionLocal

router = APIRouter()

@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    current_user: User = Depends(deps.get_current_user)
) -> StreamingResponse:
    """
    Stream the AI's response using Server-Sent Events (SSE).
    """
    return StreamingResponse(
        chat_service.chat_stream(request, current_user),
        media_type="text/event-stream"
    )

@router.get("/conversations", response_model=List[ConversationSchema])
async def get_conversations(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Fetch all conversations for the authenticated user."""
    async with AsyncSessionLocal() as db:
        stmt = select(Conversation).where(
            Conversation.user_id == current_user.id
        ).order_by(Conversation.updated_at.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageSchema])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Fetch the message history for a specific conversation."""
    async with AsyncSessionLocal() as db:
        # First verify ownership
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        result = await db.execute(stmt)
        conv = result.scalars().first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        msg_stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc())
        
        msg_result = await db.execute(msg_stmt)
        return msg_result.scalars().all()
