"""Pydantic schemas for User model."""

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User information response."""

    id: str = Field(..., description="Internal user ID (UUID)")
    discord_id: str = Field(..., description="Discord user snowflake ID")
    notification_preferences: dict = Field(
        default_factory=dict, description="User notification settings"
    )
    created_at: str = Field(..., description="Account creation timestamp (UTC ISO)")
    updated_at: str = Field(..., description="Last update timestamp (UTC ISO)")

    model_config = {"from_attributes": True}


class UserPreferencesRequest(BaseModel):
    """Update user notification preferences."""

    notification_preferences: dict = Field(
        ...,
        description=(
            "Notification settings (e.g., {'dm_reminders': true, 'email_notifications': false})"
        ),
    )
