"""
Participant-related Pydantic schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ParticipantResponse(BaseModel):
    """Game participant information."""
    id: UUID = Field(..., description="Participant record ID")
    discord_id: str | None = Field(None, description="Discord user ID (None for placeholders)")
    display_name: str | None = Field(None, description="Resolved display name or placeholder text")
    joined_at: datetime = Field(..., description="When participant joined (UTC)")
    status: str = Field(..., description="Participant status (JOINED, DROPPED, WAITLIST, PLACEHOLDER)")
    is_pre_populated: bool = Field(..., description="Whether added at game creation time")

    class Config:
        from_attributes = True


class ParticipantValidationError(BaseModel):
    """Validation error for invalid @mentions."""
    input: str = Field(..., description="Original input that failed validation")
    reason: str = Field(..., description="Why validation failed")
    suggestions: list['ParticipantSuggestion'] = Field(
        default_factory=list,
        description="Suggested matches for disambiguation"
    )


class ParticipantSuggestion(BaseModel):
    """Suggested participant match for disambiguation."""
    discord_id: str = Field(..., description="Discord user ID")
    username: str = Field(..., description="Discord username")
    display_name: str = Field(..., description="Resolved display name in guild")

    class Config:
        from_attributes = True


# Update forward reference
ParticipantValidationError.model_rebuild()
