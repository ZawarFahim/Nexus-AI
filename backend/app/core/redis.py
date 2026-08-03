import json
import logging
from typing import Any, Optional, Dict
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisManager:
    """
    Redis Connection Manager for caching and state management.
    Handles connection lifecycle and provides base utility functions.
    """
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis.")

    # -----------------------------
    # Utility Functions
    # -----------------------------
    
    async def set_json(self, key: str, value: Any, expire_seconds: int = 3600) -> None:
        """Store JSON-serializable data with an expiration time."""
        if self.redis:
            await self.redis.set(key, json.dumps(value), ex=expire_seconds)

    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and deserialize JSON data."""
        if self.redis:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        return None

    async def delete(self, key: str) -> None:
        """Delete a specific key."""
        if self.redis:
            await self.redis.delete(key)

# Global connection manager instance
redis_manager = RedisManager()

# -----------------------------
# Specific Cache Interfaces
# -----------------------------

class SessionCache:
    """Manages User Session caching logic."""
    PREFIX = "session:"
    DEFAULT_EXPIRE = 86400  # 1 day

    @staticmethod
    async def set_session(session_id: str, user_data: Dict[str, Any]) -> None:
        key = f"{SessionCache.PREFIX}{session_id}"
        await redis_manager.set_json(key, user_data, SessionCache.DEFAULT_EXPIRE)

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        key = f"{SessionCache.PREFIX}{session_id}"
        return await redis_manager.get_json(key)
        
    @staticmethod
    async def delete_session(session_id: str) -> None:
        key = f"{SessionCache.PREFIX}{session_id}"
        await redis_manager.delete(key)


class WorkflowCache:
    """Manages temporary Workflow state during execution."""
    PREFIX = "workflow_state:"
    DEFAULT_EXPIRE = 3600 * 24 * 7  # 1 week max state holding

    @staticmethod
    async def save_state(workflow_id: str, state_data: Dict[str, Any]) -> None:
        key = f"{WorkflowCache.PREFIX}{workflow_id}"
        await redis_manager.set_json(key, state_data, WorkflowCache.DEFAULT_EXPIRE)

    @staticmethod
    async def get_state(workflow_id: str) -> Optional[Dict[str, Any]]:
        key = f"{WorkflowCache.PREFIX}{workflow_id}"
        return await redis_manager.get_json(key)

    @staticmethod
    async def clear_state(workflow_id: str) -> None:
        key = f"{WorkflowCache.PREFIX}{workflow_id}"
        await redis_manager.delete(key)
