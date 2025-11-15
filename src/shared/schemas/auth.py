"""
Authentication and user-related Pydantic schemas.
"""

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """Discord user information."""
    discord_id: str = Field(..., description="Discord user ID (snowflake)")
    username: str = Field(..., description="Discord username")
    global_name: str | None = Field(None, description="Discord global display name")
    avatar: str | None = Field(None, description="Discord avatar hash")

    class Config:
        from_attributes = True


class GuildInfo(BaseModel):
    """Discord guild information."""
    guild_id: str = Field(..., description="Discord guild ID (snowflake)")
    name: str = Field(..., description="Guild name")
    icon: str | None = Field(None, description="Guild icon hash")
    owner: bool = Field(..., description="Whether user owns this guild")
    permissions: str = Field(..., description="User's permissions in guild (bitfield)")

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """OAuth2 login response."""
    access_token: str = Field(..., description="Discord access token")
    refresh_token: str = Field(..., description="Discord refresh token")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: UserInfo = Field(..., description="Authenticated user information")
    guilds: list[GuildInfo] = Field(..., description="User's guilds with bot access")

    class Config:
        from_attributes = True
