from typing import Any
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core.oauth import oauth
from app.core import security
from app.crud import crud_oauth
from app.models.user import User

router = APIRouter()

async def get_current_user_from_token(token: str, db: AsyncSession) -> User | None:
    try:
        payload = security.verify_token(token)
        if payload and "sub" in payload:
            stmt = select(User).where(User.id == payload["sub"])
            result = await db.execute(stmt)
            return result.scalars().first()
    except Exception:
        pass
    return None

def build_popup_response(access_token: str, refresh_token: str) -> HTMLResponse:
    html = f"""
    <html>
    <body>
    <script>
    if (window.opener) {{
        window.opener.postMessage({{ 
            type: 'oauth_complete', 
            access_token: '{access_token}', 
            refresh_token: '{refresh_token}' 
        }}, '*');
        window.close();
    }} else {{
        window.location.href = '/dashboard';
    }}
    </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.get("/google/login")
async def login_via_google(request: Request, redirect: str | None = None, token: str | None = None) -> Any:
    if redirect:
        request.session['oauth_redirect'] = redirect
    if token:
        request.session['connect_token'] = token
        
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_via_google(request: Request, db: AsyncSession = Depends(deps.get_db)) -> Any:
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {{e}}")
        
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not fetch user info from Google")
        
    connect_token = request.session.pop('connect_token', None)
    frontend_redirect = request.session.pop('oauth_redirect', None)
    
    current_user = None
    if connect_token:
        current_user = await get_current_user_from_token(connect_token, db)
        
    if current_user:
        await crud_oauth.link_oauth_account(db, current_user, "google", user_info, token)
        user = current_user
    else:
        user = await crud_oauth.get_or_create_google_user(db=db, profile=user_info, token=token)
    
    access_token = security.create_access_token(subject=str(user.id))
    refresh_token = security.create_refresh_token(subject=str(user.id))
    
    if frontend_redirect == 'popup':
        return build_popup_response(access_token, refresh_token)
    
    frontend_url = "http://localhost:3000/login"
    query = f"?access_token={{access_token}}&refresh_token={{refresh_token}}"
    if frontend_redirect:
        query += f"&redirect={{frontend_redirect}}"
        
    return RedirectResponse(url=f"{{frontend_url}}{{query}}")

@router.get("/github/login")
async def login_via_github(request: Request, redirect: str | None = None, token: str | None = None) -> Any:
    if redirect:
        request.session['oauth_redirect'] = redirect
    if token:
        request.session['connect_token'] = token
        
    redirect_uri = request.url_for('auth_via_github')
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/github/callback")
async def auth_via_github(request: Request, db: AsyncSession = Depends(deps.get_db)) -> Any:
    try:
        token = await oauth.github.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {{e}}")
        
    resp = await oauth.github.get('user', token=token)
    user_info = resp.json()
    
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not fetch user info from GitHub")
        
    connect_token = request.session.pop('connect_token', None)
    frontend_redirect = request.session.pop('oauth_redirect', None)
    
    current_user = None
    if connect_token:
        current_user = await get_current_user_from_token(connect_token, db)
        
    if current_user:
        await crud_oauth.link_oauth_account(db, current_user, "github", user_info, token)
        user = current_user
    else:
        raise HTTPException(status_code=400, detail="Must be logged in to connect GitHub account")
    
    access_token = security.create_access_token(subject=str(user.id))
    refresh_token = security.create_refresh_token(subject=str(user.id))
    
    if frontend_redirect == 'popup':
        return build_popup_response(access_token, refresh_token)
    
    frontend_url = "http://localhost:3000/login"
    query = f"?access_token={{access_token}}&refresh_token={{refresh_token}}"
    if frontend_redirect:
        query += f"&redirect={{frontend_redirect}}"
        
    return RedirectResponse(url=f"{{frontend_url}}{{query}}")
