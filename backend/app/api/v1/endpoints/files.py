from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
import uuid
from pydantic import BaseModel
import io

from app.api import deps
from app.models.user import User
from app.services.rag_service import rag_service

router = APIRouter()

class FileResponse(BaseModel):
    document_id: str
    filename: str
    message: str

@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Upload a file, extract text, and index it into the RAG pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Read the file content
    content = await file.read()
    
    # Try to decode text based on basic types
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        # Very simple fallback for PDFs (in reality, you'd use PyPDF2 or pdfminer)
        # For MVP we will just reject non-utf8 files
        raise HTTPException(
            status_code=400, 
            detail="File must be a valid UTF-8 text or markdown file for this MVP."
        )

    document_id = str(uuid.uuid4())
    
    # Index into RAG service
    await rag_service.index_document(
        document_id=document_id,
        title=file.filename,
        text=text,
        metadata={"user_id": str(current_user.id)}
    )

    # Save to Database
    from app.models.file import FileMetadata
    from app.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        new_file = FileMetadata(
            user_id=current_user.id,
            filename=file.filename,
            file_type=file.content_type,
            size_bytes=len(content),
            qdrant_document_id=document_id
        )
        db.add(new_file)
        await db.commit()

    return FileResponse(
        document_id=document_id,
        filename=file.filename,
        message=f"Successfully indexed {file.filename} into RAG memory."
    )
