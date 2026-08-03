from fastapi import APIRouter
from app.core.qdrant import qdrant_manager
from app.core.redis import redis_manager

router = APIRouter()

@router.get("/health", status_code=200)
async def health_check():
    qdrant_ok = await qdrant_manager.health_check()
    redis_ok = redis_manager.redis is not None
    
    if redis_ok:
        try:
            await redis_manager.redis.ping()
        except Exception:
            redis_ok = False

    return {
        "status": "ok" if (qdrant_ok and redis_ok) else "degraded",
        "message": "Service is running",
        "services": {
            "qdrant": "healthy" if qdrant_ok else "unhealthy",
            "redis": "healthy" if redis_ok else "unhealthy"
        }
    }
