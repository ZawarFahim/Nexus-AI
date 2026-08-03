from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router

from contextlib import asynccontextmanager
from app.core.redis import redis_manager
from app.core.qdrant import qdrant_manager

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await redis_manager.connect()
    await qdrant_manager.connect()
    
    # Initialize default memory collection
    try:
        await qdrant_manager.initialize_collection("nexus_memories")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not initialize default collection: {e}")
        
    yield
    
    # Shutdown
    await qdrant_manager.disconnect()
    await redis_manager.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS configuration
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}
