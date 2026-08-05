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
    
    response_data = SettingsResponse.model_validate(settings)
    if oauth_account and oauth_account.access_token:
        response_data.google_connected = True
        response_data.google_email = current_user.email
        
    return response_data

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
    
    response_data = SettingsResponse.model_validate(settings)
    if oauth_account and oauth_account.access_token:
        response_data.google_connected = True
        response_data.google_email = current_user.email
        
    return response_data
