"""
Guild and channel configuration Pydantic schemas.
"""


from pydantic import BaseModel, Field, validator


class GuildConfigRequest(BaseModel):
    """Request schema for updating guild configuration."""
    default_max_players: int | None = Field(None, ge=2, le=50, description="Default max players for guild")
    default_reminder_minutes: list[int] | None = Field(None, description="Default reminder times")
    default_rules: str | None = Field(None, max_length=5000, description="Default game rules")
    allowed_host_role_ids: list[str] | None = Field(None, description="Role IDs allowed to host games")
    require_host_role: bool | None = Field(None, description="Whether host role is required")

    @validator('default_reminder_minutes')
    def validate_reminder_minutes(cls, v):
        if v is not None:
            if len(v) > 10:
                raise ValueError("Cannot have more than 10 reminder times")
            if any(minutes < 0 or minutes > 10080 for minutes in v):
                raise ValueError("Reminder minutes must be between 0 and 10080 (1 week)")
        return v


class GuildConfigResponse(BaseModel):
    """Guild configuration response."""
    guild_id: str = Field(..., description="Discord guild ID")
    guild_name: str = Field(..., description="Guild name")
    default_max_players: int = Field(..., description="Default max players")
    default_reminder_minutes: list[int] = Field(..., description="Default reminder times")
    default_rules: str | None = Field(None, description="Default game rules")
    allowed_host_role_ids: list[str] = Field(..., description="Allowed host role IDs")
    require_host_role: bool = Field(..., description="Whether host role is required")

    class Config:
        from_attributes = True


class ChannelConfigRequest(BaseModel):
    """Request schema for updating channel configuration."""
    is_active: bool | None = Field(None, description="Enable/disable game posting in channel")
    max_players: int | None = Field(None, ge=2, le=50, description="Channel max players override")
    reminder_minutes: list[int] | None = Field(None, description="Channel reminder times override")
    default_rules: str | None = Field(None, max_length=5000, description="Channel rules override")
    allowed_host_role_ids: list[str] | None = Field(None, description="Channel host roles override")
    game_category: str | None = Field(None, max_length=100, description="Game category for channel")

    @validator('reminder_minutes')
    def validate_reminder_minutes(cls, v):
        if v is not None:
            if len(v) > 10:
                raise ValueError("Cannot have more than 10 reminder times")
            if any(minutes < 0 or minutes > 10080 for minutes in v):
                raise ValueError("Reminder minutes must be between 0 and 10080 (1 week)")
        return v


class ChannelConfigResponse(BaseModel):
    """Channel configuration response with inheritance."""
    channel_id: str = Field(..., description="Discord channel ID")
    channel_name: str = Field(..., description="Channel name")
    guild_id: str = Field(..., description="Parent guild ID")
    is_active: bool = Field(..., description="Whether channel is active for games")
    max_players: int | None = Field(None, description="Channel override for max players")
    reminder_minutes: list[int] | None = Field(None, description="Channel override for reminders")
    default_rules: str | None = Field(None, description="Channel override for rules")
    allowed_host_role_ids: list[str] | None = Field(None, description="Channel override for host roles")
    game_category: str | None = Field(None, description="Game category")

    # Resolved values (with inheritance)
    resolved_max_players: int = Field(..., description="Final max players (with inheritance)")
    resolved_reminder_minutes: list[int] = Field(..., description="Final reminder times (with inheritance)")
    resolved_rules: str | None = Field(None, description="Final rules (with inheritance)")
    resolved_host_role_ids: list[str] = Field(..., description="Final host roles (with inheritance)")

    class Config:
        from_attributes = True
