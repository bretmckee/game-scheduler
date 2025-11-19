"""Pydantic schemas for authentication endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request to initiate OAuth2 login flow."""

    redirect_uri: str | None = Field(None, description="Optional redirect URI after authentication")


class LoginResponse(BaseModel):
    """OAuth2 authorization URL response."""

    authorization_url: str = Field(..., description="Discord OAuth2 authorization URL")
    state: str = Field(..., description="CSRF protection state token")


class OAuthCallbackRequest(BaseModel):
    """OAuth2 callback parameters."""

    code: str = Field(..., description="Authorization code from Discord")
    state: str = Field(..., description="State token for CSRF verification")


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str = Field(..., description="Discord access token")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., description="Refresh token from previous auth")


class UserInfoResponse(BaseModel):
    """Discord user information response."""

    id: str = Field(..., description="Discord user snowflake ID")
    user_uuid: str = Field(..., description="Database user UUID")
    username: str = Field(..., description="Discord username")
    avatar: str | None = Field(None, description="Avatar hash")
    guilds: list[dict] = Field(default_factory=list, description="User's guilds")


class CurrentUser(BaseModel):
    """Current authenticated user information."""

    user: Any = Field(..., description="Authenticated user model")
    access_token: str = Field(..., description="Discord access token")
    session_token: str = Field(..., description="Session token for Redis lookup")

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}
