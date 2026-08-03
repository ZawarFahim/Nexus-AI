import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class MemoryCreate(BaseModel):
    content: str = Field(..., description="The core content of the memory.")
    category: str = Field("General", description="A categorization tag for the memory.")
    title: Optional[str] = Field(None, description="An optional short title.")

class MemoryResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    content: str
    category: str
    importance_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MemorySearchRequest(BaseModel):
    query: str = Field(..., description="The natural language search query.")
    limit: int = Field(5, description="Maximum number of results to return.", ge=1, le=20)
    category: Optional[str] = Field(None, description="Optional category to filter by.")
    min_importance: Optional[float] = Field(0.0, description="Minimum importance score (1-10).")
