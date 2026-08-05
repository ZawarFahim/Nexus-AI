from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.models.user import User
from app.models.settings import Settings
from app.schemas.settings import SettingsUpdate, SettingsInDB, SettingsResponse
from app.models.settings import OAuthAccount

router = APIRouter()

@router.get("/", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get user settings.
    """
    stmt = select(Settings).where(Settings.user_id == current_user.id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = Settings(user_id=current_user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    # Check Google OAuth status
    oauth_stmt = select(OAuthAccount).where(
        OAuthAccount.user_id == current_user.id,
        OAuthAccount.provider == "google"
    )
    oauth_result = await db.execute(oauth_stmt)
    oauth_account = oauth_result.scalar_one_or_none()
    
    response_dict = {
        "id": str(settings.id),
        "user_id": str(settings.user_id),
        "theme": settings.theme,
        "language": settings.language,
        "voice_enabled": settings.voice_enabled,
        "default_llm": settings.default_llm,
        "notifications_enabled": settings.notifications_enabled,
        "github_pat": settings.github_pat,
        "n8n_webhook_url": settings.n8n_webhook_url,
        "n8n_api_key": settings.n8n_api_key,
        "google_connected": bool(oauth_account and oauth_account.access_token),
        "google_email": current_user.email if (oauth_account and oauth_account.access_token) else None
    }
    return response_dict

@router.put("/", response_model=SettingsResponse)
async def update_settings(
    *,
    db: AsyncSession = Depends(deps.get_db),
    settings_in: SettingsUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update user settings.
    """
    stmt = select(Settings).where(Settings.user_id == current_user.id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = Settings(user_id=current_user.id)
        db.add(settings)
        
    update_data = settings_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(settings, field, update_data[field])
        
    await db.commit()
    await db.refresh(settings)
    
    # Check Google OAuth status for response
    oauth_stmt = select(OAuthAccount).where(
        OAuthAccount.user_id == current_user.id,
        OAuthAccount.provider == "google"
    )
    oauth_result = await db.execute(oauth_stmt)
    oauth_account = oauth_result.scalar_one_or_none()
    
    response_dict = {
        "id": str(settings.id),
        "user_id": str(settings.user_id),
        "theme": settings.theme,
        "language": settings.language,
        "voice_enabled": settings.voice_enabled,
        "default_llm": settings.default_llm,
        "notifications_enabled": settings.notifications_enabled,
        "github_pat": settings.github_pat,
        "n8n_webhook_url": settings.n8n_webhook_url,
        "n8n_api_key": settings.n8n_api_key,
        "google_connected": bool(oauth_account and oauth_account.access_token),
        "google_email": current_user.email if (oauth_account and oauth_account.access_token) else None
    }
    return response_dict
