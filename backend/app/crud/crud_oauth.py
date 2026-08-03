import uuid
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.settings import OAuthAccount
from app.core.security import encrypt_token

async def get_or_create_google_user(db: AsyncSession, profile: Dict[str, Any], token: Dict[str, Any]) -> User:
    """Find a user by Google email, or create them. Then save/update their OAuth tokens."""
    email = profile.get("email")
    if not email:
        raise ValueError("Google profile did not return an email.")

    # Find existing user
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        # Create a new user with a random un-usable password hash
        user = User(
            email=email,
            full_name=profile.get("name"),
            profile_image=profile.get("picture"),
            password_hash="!oauth_login_no_password_set!",
            is_verified=profile.get("email_verified", False)
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Check if they have an existing OAuth account record
    oauth_stmt = select(OAuthAccount).where(
        OAuthAccount.user_id == user.id,
        OAuthAccount.provider == "google"
    )
    oauth_result = await db.execute(oauth_stmt)
    oauth_account = oauth_result.scalars().first()

    access_token = token.get("access_token", "")
    refresh_token = token.get("refresh_token")
    expires_at = token.get("expires_at")
    
    if refresh_token:
        # Encrypt the refresh token before saving
        refresh_token = encrypt_token(refresh_token)

    if oauth_account:
        # Update tokens
        oauth_account.access_token = access_token
        if refresh_token:
            oauth_account.refresh_token = refresh_token
        if expires_at:
            from datetime import datetime
            oauth_account.expires_at = datetime.fromtimestamp(expires_at)
    else:
        # Create new OAuth account link
        from datetime import datetime
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=profile.get("sub", ""),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.fromtimestamp(expires_at) if expires_at else None
        )
        db.add(oauth_account)

    await db.commit()
    
    return user
