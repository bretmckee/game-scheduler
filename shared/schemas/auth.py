# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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
