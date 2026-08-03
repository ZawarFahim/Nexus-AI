import logging
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest
from app.core.config import settings

logger = logging.getLogger(__name__)

class QdrantManager:
    """
    Qdrant Connection and Vector Management.
    Handles semantic vector embeddings for long-term memory and retrieval.
    """
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None

    async def connect(self) -> None:
        """Initialize Qdrant client."""
        try:
            self.client = AsyncQdrantClient(url=settings.QDRANT_URL)
            # Perform a ping/health check to verify connection
            await self.client.get_collections()
            logger.info("Connected to Qdrant successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Qdrant client connection."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Qdrant.")

    async def initialize_collection(self, collection_name: str, vector_size: int = 768, distance=rest.Distance.COSINE) -> None:
        """Initialize a new collection if it does not exist."""
        if not self.client:
            raise RuntimeError("Qdrant client not connected.")
        
        try:
            collections = await self.client.get_collections()
            exists = any(c.name == collection_name for c in collections.collections)
            
            if not exists:
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=rest.VectorParams(
                        size=vector_size,
                        distance=distance,
                    )
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error initializing Qdrant collection {collection_name}: {e}")
            raise

    async def insert_vectors(self, collection_name: str, points: List[rest.PointStruct]) -> None:
        """Insert a batch of vectors (points) into a collection."""
        if not self.client:
            raise RuntimeError("Qdrant client not connected.")
        
        await self.client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )

    async def search_vectors(self, collection_name: str, query_vector: List[float], limit: int = 5, query_filter: Optional[rest.Filter] = None) -> List[rest.ScoredPoint]:
        """Search for similar vectors in a collection."""
        if not self.client:
            raise RuntimeError("Qdrant client not connected.")
        
        return await self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit
        )

    async def delete_vectors(self, collection_name: str, point_ids: List[str]) -> None:
        """Delete specific vectors from a collection by their IDs."""
        if not self.client:
            raise RuntimeError("Qdrant client not connected.")
        
        await self.client.delete(
            collection_name=collection_name,
            points_selector=rest.PointIdsList(
                points=point_ids,
            ),
            wait=True
        )

    async def health_check(self) -> bool:
        """Return True if connected and responsive."""
        if not self.client:
            return False
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False

# Global Qdrant manager instance
qdrant_manager = QdrantManager()
