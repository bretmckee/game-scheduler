"""Pydantic schemas for Game participants."""

from pydantic import BaseModel, Field


class ParticipantJoinRequest(BaseModel):
    """Request to join a game."""

    user_discord_id: str = Field(..., description="Discord user snowflake ID")


class ParticipantResponse(BaseModel):
    """Game participant response."""

    id: str = Field(..., description="Participant ID (UUID)")
    game_session_id: str = Field(..., description="Game session ID (UUID)")
    user_id: str | None = Field(None, description="User ID (UUID) - None for placeholder entries")
    discord_id: str | None = Field(None, description="Discord snowflake ID - None for placeholders")
    display_name: str | None = Field(
        None,
        description="Resolved display name (guild-specific or placeholder text)",
    )
    joined_at: str = Field(..., description="Join timestamp (UTC ISO)")
    pre_filled_position: int | None = Field(
        None,
        description="Position in pre-populated list (1-indexed, None for regular participants)",
    )

    model_config = {"from_attributes": True}
