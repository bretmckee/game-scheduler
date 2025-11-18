"""
Authentication routes for Discord OAuth2 flow.

Handles login, callback, refresh, logout, and user info endpoints.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.auth import oauth2, tokens
from services.api.config import get_api_config
from services.api.dependencies import auth as auth_deps
from shared.database import get_db_session
from shared.models import user as user_model
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/login")
async def login(redirect_uri: str = Query(...)) -> auth_schemas.LoginResponse:
    """
    Initiate Discord OAuth2 login flow.

    Args:
        redirect_uri: URL to redirect to after authorization

    Returns:
        Authorization URL and state token
    """
    try:
        auth_url, state = await oauth2.generate_authorization_url(redirect_uri)
        return auth_schemas.LoginResponse(authorization_url=auth_url, state=state)
    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login") from e


@router.get("/callback", response_model=None)
async def callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle Discord OAuth2 callback.

    Args:
        code: Authorization code from Discord
        state: State token for CSRF protection
        db: Database session

    Returns:
        Redirect to frontend or HTML success page
    """
    try:
        redirect_uri = await oauth2.validate_state(state)
    except oauth2.OAuth2StateError as e:
        raise HTTPException(status_code=400, detail="Invalid or expired state") from e

    try:
        token_data = await oauth2.exchange_code_for_tokens(code, redirect_uri)
        user_data = await oauth2.get_user_from_token(token_data["access_token"])
    except Exception as e:
        logger.error(f"OAuth2 callback failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed") from e

    discord_id = user_data["id"]

    from sqlalchemy import select

    result = await db.execute(
        select(user_model.User).where(user_model.User.discord_id == discord_id)
    )
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        new_user = user_model.User(discord_id=discord_id)
        db.add(new_user)
        await db.commit()
        logger.info(f"Created new user with Discord ID: {discord_id}")

    await tokens.store_user_tokens(
        discord_id,
        token_data["access_token"],
        token_data["refresh_token"],
        token_data["expires_in"],
    )

    config = get_api_config()

    # Check if there's a frontend to redirect to, otherwise show success page
    if config.frontend_url and config.frontend_url != "http://localhost:3000":
        return RedirectResponse(url=f"{config.frontend_url}?success=true&user_id={discord_id}")

    # Return a simple success page for testing without a frontend
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login Successful</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 500px;
            }}
            h1 {{ color: #5865F2; margin-bottom: 20px; }}
            .success {{ color: #43b581; font-size: 24px; margin: 20px 0; }}
            code {{
                background: #f0f0f0;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }}
            .info {{ margin: 20px 0; text-align: left; }}
            .info p {{ margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ Discord Login Successful!</h1>
            <div class="success">Authentication Complete</div>
            <div class="info">
                <p><strong>Your Discord ID:</strong> <code>{discord_id}</code></p>
                <p><strong>Status:</strong> Tokens stored securely in Redis</p>
                <p><strong>Session:</strong> Valid for 24 hours</p>
            </div>
            <p style="margin-top: 30px; color: #666;">
                You can now close this window and use the API with your Discord ID.
            </p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/refresh")
async def refresh(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
) -> auth_schemas.TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        current_user: Current authenticated user

    Returns:
        New token data
    """
    token_data = await tokens.get_user_tokens(current_user.discord_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="No session found")

    try:
        new_tokens = await oauth2.refresh_access_token(token_data["refresh_token"])
        await tokens.refresh_user_tokens(
            current_user.discord_id,
            new_tokens["access_token"],
            new_tokens["refresh_token"],
            new_tokens["expires_in"],
        )

        return auth_schemas.TokenResponse(
            access_token=new_tokens["access_token"],
            expires_in=new_tokens["expires_in"],
        )
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh token") from e


@router.post("/logout")
async def logout(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
) -> dict[str, str]:
    """
    Logout user and delete session.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    await tokens.delete_user_tokens(current_user.discord_id)
    return {"message": "Logged out successfully"}


@router.get("/user", response_model=auth_schemas.UserInfoResponse)
async def get_user_info(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
) -> auth_schemas.UserInfoResponse:
    """
    Get current user information and guilds.

    Args:
        current_user: Current authenticated user

    Returns:
        User info and guild list
    """
    token_data = await tokens.get_user_tokens(current_user.discord_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="No session found")

    if await tokens.is_token_expired(token_data["expires_at"]):
        try:
            new_tokens = await oauth2.refresh_access_token(token_data["refresh_token"])
            await tokens.refresh_user_tokens(
                current_user.discord_id,
                new_tokens["access_token"],
                new_tokens["refresh_token"],
                new_tokens["expires_in"],
            )
            access_token = new_tokens["access_token"]
        except Exception as e:
            logger.error(f"Token refresh in get_user_info failed: {e}")
            raise HTTPException(status_code=401, detail="Session expired") from e
    else:
        access_token = token_data["access_token"]

    try:
        user_info = await oauth2.get_user_from_token(access_token)
        guilds = await oauth2.get_user_guilds(access_token)

        return auth_schemas.UserInfoResponse(
            id=user_info["id"],
            username=user_info["username"],
            avatar=user_info.get("avatar"),
            guilds=guilds,
        )
    except Exception as e:
        logger.error(f"Failed to fetch user info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user info") from e
