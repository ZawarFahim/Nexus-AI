from typing import Any
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.oauth import oauth
from app.core import security
from app.crud import crud_oauth
from app.schemas.token import Token

router = APIRouter()

@router.get("/google/login")
async def login_via_google(request: Request, redirect: str = None):
    """
    Redirect the user to Google's consent screen.
    """
    if redirect:
        request.session['oauth_redirect'] = redirect
        
    # Assuming the API runs locally. In production, this should be the full external URL.
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

from fastapi.responses import RedirectResponse

@router.get("/google/callback")
async def auth_via_google(request: Request, db: AsyncSession = Depends(deps.get_db)) -> Any:
    """
    Handle Google OAuth callback, provision user, and redirect to frontend.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {e}")
        
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not fetch user info from Google")
        
    user = await crud_oauth.get_or_create_google_user(db=db, profile=user_info, token=token)
    
    access_token = security.create_access_token(subject=user.id)
    refresh_token = security.create_refresh_token(subject=user.id)
    
    frontend_url = "http://localhost:3000/login"
    query = f"?access_token={access_token}&refresh_token={refresh_token}"
    
    frontend_redirect = request.session.pop('oauth_redirect', None)
    if frontend_redirect:
        query += f"&redirect={frontend_redirect}"
        
    response = RedirectResponse(url=f"{frontend_url}{query}")
    return response
