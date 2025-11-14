"""
Game-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator

from .participant import ParticipantResponse


class CreateGameRequest(BaseModel):
    """Request schema for creating a new game session."""
    title: str = Field(..., min_length=1, max_length=200, description="Game title")
    description: str = Field(..., min_length=1, max_length=2000, description="Game description")
    scheduled_at: datetime = Field(..., description="Game start time (ISO 8601 UTC)")
    guild_id: str = Field(..., description="Discord guild ID where game will be posted")
    channel_id: str = Field(..., description="Discord channel ID for game announcements")
    max_players: Optional[int] = Field(None, ge=2, le=50, description="Maximum players (inherits if None)")
    reminder_minutes: Optional[List[int]] = Field(None, description="Reminder times before game starts")
    rules: Optional[str] = Field(None, max_length=5000, description="Game rules (inherits if None)")
    initial_participants: Optional[List[str]] = Field(
        default_factory=list, 
        description="@mentions or placeholder strings for pre-populating participants"
    )
    
    @validator('reminder_minutes')
    def validate_reminder_minutes(cls, v):
        if v is not None:
            if len(v) > 10:
                raise ValueError("Cannot have more than 10 reminder times")
            if any(minutes < 0 or minutes > 10080 for minutes in v):  # 1 week max
                raise ValueError("Reminder minutes must be between 0 and 10080 (1 week)")
        return v


class UpdateGameRequest(BaseModel):
    """Request schema for updating an existing game."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    scheduled_at: Optional[datetime] = Field(None, description="Game start time (ISO 8601 UTC)")
    max_players: Optional[int] = Field(None, ge=2, le=50)
    reminder_minutes: Optional[List[int]] = Field(None)
    rules: Optional[str] = Field(None, max_length=5000)
    
    @validator('reminder_minutes')
    def validate_reminder_minutes(cls, v):
        if v is not None:
            if len(v) > 10:
                raise ValueError("Cannot have more than 10 reminder times")
            if any(minutes < 0 or minutes > 10080 for minutes in v):
                raise ValueError("Reminder minutes must be between 0 and 10080 (1 week)")
        return v


class GameResponse(BaseModel):
    """Basic game information response."""
    id: UUID = Field(..., description="Game session UUID")
    title: str = Field(..., description="Game title")
    description: str = Field(..., description="Game description")
    scheduled_at: datetime = Field(..., description="Game start time (UTC)")
    guild_id: str = Field(..., description="Discord guild ID")
    channel_id: str = Field(..., description="Discord channel ID")
    host_discord_id: str = Field(..., description="Host's Discord ID")
    max_players: int = Field(..., description="Maximum players (resolved with inheritance)")
    participant_count: int = Field(..., description="Current number of participants")
    status: str = Field(..., description="Game status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)")
    created_at: datetime = Field(..., description="Game creation time (UTC)")
    
    class Config:
        from_attributes = True


class GameDetailsResponse(GameResponse):
    """Detailed game information with participants and settings."""
    participants: List[ParticipantResponse] = Field(..., description="Game participants")
    reminder_minutes: List[int] = Field(..., description="Reminder times (resolved with inheritance)")
    rules: Optional[str] = Field(None, description="Game rules (resolved with inheritance)")
    message_id: Optional[str] = Field(None, description="Discord message ID")
    
    class Config:
        from_attributes = True


class JoinGameResponse(BaseModel):
    """Response when joining a game."""
    success: bool = Field(..., description="Whether join was successful")
    message: str = Field(..., description="Success or error message")
    participant_count: int = Field(..., description="Updated participant count")
    is_full: bool = Field(..., description="Whether game is now full")
    
    class Config:
        from_attributes = True