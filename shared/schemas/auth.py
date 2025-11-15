"""Pydantic schemas for authentication endpoints."""

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
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: str | None = Field(
        None, description="Refresh token for obtaining new access tokens"
    )
    scope: str = Field(..., description="Granted OAuth2 scopes")


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., description="Refresh token from previous auth")


class UserInfoResponse(BaseModel):
    """Discord user information response."""

    id: str = Field(..., description="Discord user snowflake ID")
    username: str = Field(..., description="Discord username")
    discriminator: str = Field(..., description="Discord discriminator (legacy)")
    avatar: str | None = Field(None, description="Avatar hash")
    global_name: str | None = Field(None, description="User's global display name")
    email: str | None = Field(None, description="User email (requires email scope)")
