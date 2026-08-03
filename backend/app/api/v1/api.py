from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, oauth, planner, mcp, coordinator, chat

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
api_router.include_router(coordinator.router, prefix="/coordinator", tags=["coordinator"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])



