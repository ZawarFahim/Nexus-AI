import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's input message.")
    conversation_id: Optional[uuid.UUID] = Field(None, description="The ID of the conversation if continuing an existing chat.")

class MessageSchema(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationSchema(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageSchema]] = None

    class Config:
        from_attributes = True

class ChatStreamResponse(BaseModel):
    chunk: str
    conversation_id: uuid.UUID
