from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.api import deps
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryResponse, MemorySearchRequest
from app.services.memory_service import memory_service

router = APIRouter()

@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: MemoryCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Store a new memory. The system will automatically evaluate its importance
    and generate a semantic embedding before saving it to Qdrant and PostgreSQL.
    """
    try:
        return await memory_service.save_memory(current_user, request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save memory: {str(e)}"
        )

@router.post("/search", response_model=List[MemoryResponse])
async def search_memories(
    request: MemorySearchRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Perform a semantic search across the user's memories using vector similarity.
    """
    try:
        return await memory_service.search_memory(current_user, request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )
