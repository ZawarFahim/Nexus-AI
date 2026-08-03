from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, oauth, planner

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])


