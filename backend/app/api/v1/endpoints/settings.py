from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.models.user import User
from app.models.settings import Settings
from app.schemas.settings import SettingsUpdate, SettingsInDB

router = APIRouter()

@router.get("/", response_model=SettingsInDB)
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
        
    return settings

@router.put("/", response_model=SettingsInDB)
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
    return settings
