import logging
import uuid
import json
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range
from google import genai
from google.genai import types
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User
from app.models.memory import Memory, Embedding
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryResponse
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = "nexus_memories"
        
        if settings.GEMINI_API_KEY:
            self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.genai_client = None
            
        self._ensure_collection()

    def _ensure_collection(self):
        """Initialize the Qdrant collection if it doesn't exist."""
        try:
            collections = self.qdrant.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                # text-embedding-004 has 768 dimensions
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")

    async def _calculate_importance(self, content: str) -> float:
        """Use the LLM to grade the memory on a scale of 1-10."""
        if not self.genai_client:
            return 5.0
            
        prompt = (
            "You are evaluating the importance of a memory for a user's personal assistant.\n"
            "Rate how important this memory is to remember long-term on a scale from 1.0 to 10.0.\n"
            "Only return a single float number. No text.\n\n"
            f"Memory Content: {content}"
        )
        
        try:
            response = self.genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            score = float(response.text.strip())
            return max(1.0, min(10.0, score))
        except Exception as e:
            logger.error(f"Failed to calculate importance: {e}")
            return 5.0

    async def _generate_embedding(self, content: str) -> list[float]:
        """Generate a dense vector for the memory."""
        if not self.genai_client:
            raise RuntimeError("Gemini API key not configured for embeddings.")
            
        response = self.genai_client.models.embed_content(
            model='text-embedding-004',
            contents=content
        )
        return response.embeddings[0].values

    async def save_memory(self, user: User, data: MemoryCreate) -> MemoryResponse:
        """Saves a new memory into PostgreSQL and Qdrant."""
        
        # 1. Analyze and Embed
        importance_score = await self._calculate_importance(data.content)
        vector = await self._generate_embedding(data.content)
        
        # 2. Database transaction
        async with AsyncSessionLocal() as db:
            qdrant_uuid = str(uuid.uuid4())
            memory_uuid = uuid.uuid4()
            
            # Store in PostgreSQL
            db_memory = Memory(
                id=memory_uuid,
                user_id=user.id,
                title=data.title,
                content=data.content,
                category=data.category,
                importance_score=importance_score,
                # Link to the Qdrant Point UUID
                embedding_id=uuid.UUID(qdrant_uuid)
            )
            db.add(db_memory)
            
            # Audit log in Embedding table
            db_embed = Embedding(
                memory_id=memory_uuid,
                vector_id=uuid.UUID(qdrant_uuid),
                embedding_model="text-embedding-004"
            )
            db.add(db_embed)
            
            await db.commit()
            await db.refresh(db_memory)
            
            # 3. Store in Qdrant
            # We store the memory_id and user_id in the payload for fast reverse-lookups and secure filtering
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=qdrant_uuid,
                        vector=vector,
                        payload={
                            "user_id": str(user.id),
                            "memory_id": str(memory_uuid),
                            "category": data.category,
                            "importance": importance_score
                        }
                    )
                ]
            )
            
            return MemoryResponse.model_validate(db_memory)

    async def search_memory(self, user: User, request: MemorySearchRequest) -> list[MemoryResponse]:
        """Perform a semantic search for memories belonging to this user."""
        
        query_vector = await self._generate_embedding(request.query)
        
        # Build secure filter forcing it to only match this user's vectors
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=str(user.id)))
        ]
        
        if request.category:
            must_conditions.append(FieldCondition(key="category", match=MatchValue(value=request.category)))
            
        if request.min_importance > 0:
            must_conditions.append(FieldCondition(key="importance", range=Range(gte=request.min_importance)))

        qdrant_filter = Filter(must=must_conditions)
        
        # Execute Vector Search
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=request.limit,
            with_payload=True
        )
        
        if not search_results:
            return []
            
        # Extract the memory IDs from the payloads
        memory_ids = [uuid.UUID(res.payload["memory_id"]) for res in search_results if res.payload]
        
        # Fetch the full metadata from PostgreSQL
        async with AsyncSessionLocal() as db:
            stmt = select(Memory).where(Memory.id.in_(memory_ids))
            result = await db.execute(stmt)
            memories = result.scalars().all()
            
            # Keep Qdrant's relevance ordering
            memories_by_id = {m.id: m for m in memories}
            ordered_memories = [memories_by_id[m_id] for m_id in memory_ids if m_id in memories_by_id]
            
            return [MemoryResponse.model_validate(m) for m in ordered_memories]

memory_service = MemoryService()
