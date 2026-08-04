import logging
import uuid
from typing import List, Dict, Any
from google import genai
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.core.config import settings
from app.core.qdrant import qdrant_manager
from qdrant_client.http import models as rest

logger = logging.getLogger(__name__)

COLLECTION_NAME = "nexus_documents"

class RAGService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None

    async def _ensure_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        if not qdrant_manager.client:
            return
            
        try:
            await qdrant_manager.initialize_collection(
                collection_name=COLLECTION_NAME,
                vector_size=768,
                distance=rest.Distance.COSINE
            )
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embeddings using Gemini text-embedding-004."""
        if not self.client:
            raise RuntimeError("Gemini client not configured for embeddings.")
            
        response = self.client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        return response.embeddings[0].values

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Simple text chunking with overlap."""
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
            
        return chunks

    async def index_document(self, document_id: str, title: str, text: str, metadata: Dict[str, Any] = None):
        """Chunk a document, generate embeddings, and store in Qdrant."""
        await self._ensure_collection()
        
        if not qdrant_manager.client:
            raise RuntimeError("Qdrant client not available.")
            
        chunks = self.chunk_text(text)
        points = []
        
        for i, chunk in enumerate(chunks):
            embedding = await self.get_embedding(chunk)
            
            payload = {
                "document_id": document_id,
                "title": title,
                "text": chunk,
                "chunk_index": i
            }
            if metadata:
                payload.update(metadata)
                
            points.append(rest.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            ))
            
        await qdrant_manager.insert_vectors(
            collection_name=COLLECTION_NAME,
            points=points
        )
        logger.info(f"Indexed document {title} with {len(chunks)} chunks.")

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant document chunks based on a query."""
        await self._ensure_collection()
        
        if not qdrant_manager.client:
            return []
            
        query_vector = await self.get_embedding(query)
        
        search_result = await qdrant_manager.search_vectors(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit
        )
        
        results = []
        for hit in search_result:
            results.append({
                "score": hit.score,
                "payload": hit.payload
            })
            
        return results

rag_service = RAGService()
