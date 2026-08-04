from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, oauth, planner, mcp, coordinator, chat, memory, voice, files, dashboard, settings

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
api_router.include_router(coordinator.router, prefix="/coordinator", tags=["coordinator"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
