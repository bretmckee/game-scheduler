"""Pydantic schemas for Channel configuration."""

from pydantic import BaseModel, Field


class ChannelConfigCreateRequest(BaseModel):
    """Create channel configuration."""

    guild_id: str = Field(..., description="Parent guild ID (UUID)")
    channel_id: str = Field(..., description="Discord channel snowflake ID")
    channel_name: str = Field(..., description="Discord channel name")
    is_active: bool = Field(
        default=True, description="Whether game posting is enabled in this channel"
    )
    max_players: int | None = Field(
        None, description="Max players override (overrides guild default if set)"
    )
    reminder_minutes: list[int] | None = Field(
        None,
        description="Reminder times override (overrides guild default if set)",
    )
    allowed_host_role_ids: list[str] | None = Field(
        None,
        description="Host role override (overrides guild allowed roles if set)",
    )
    game_category: str | None = Field(
        None, description="Game category for filtering (e.g., 'D&D', 'Board Games')"
    )


class ChannelConfigUpdateRequest(BaseModel):
    """Update channel configuration (all fields optional)."""

    channel_name: str | None = None
    is_active: bool | None = None
    max_players: int | None = None
    reminder_minutes: list[int] | None = None
    allowed_host_role_ids: list[str] | None = None
    game_category: str | None = None


class ChannelConfigResponse(BaseModel):
    """Channel configuration response."""

    id: str = Field(..., description="Internal channel config ID (UUID)")
    guild_id: str = Field(..., description="Parent guild ID (UUID)")
    guild_discord_id: str = Field(..., description="Discord guild snowflake ID")
    channel_id: str = Field(..., description="Discord channel snowflake ID")
    channel_id: str = Field(..., description="Discord channel snowflake ID")
    channel_name: str = Field(..., description="Discord channel name")
    is_active: bool = Field(..., description="Whether channel is active for games")
    max_players: int | None = Field(None, description="Max players override")
    reminder_minutes: list[int] | None = Field(None, description="Reminder times override")
    allowed_host_role_ids: list[str] | None = Field(None, description="Host role override")
    game_category: str | None = Field(None, description="Game category")
    created_at: str = Field(..., description="Creation timestamp (UTC ISO)")
    updated_at: str = Field(..., description="Last update timestamp (UTC ISO)")

    model_config = {"from_attributes": True}
