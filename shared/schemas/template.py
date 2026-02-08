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


"""Pydantic schemas for game templates."""

from pydantic import BaseModel, Field


class TemplateCreateRequest(BaseModel):
    """Create game template."""

    guild_id: str = Field(..., description="Guild UUID")
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: str | None = Field(None, max_length=4000, description="Template description")
    order: int = Field(default=0, ge=0, description="Sort order (0-based)")
    is_default: bool = Field(default=False, description="Whether this is the default template")

    # Locked fields (manager-only, host cannot edit)
    channel_id: str = Field(..., description="Channel UUID where games are posted")
    notify_role_ids: list[str] | None = Field(
        None, description="Role IDs to notify when game is created"
    )
    allowed_player_role_ids: list[str] | None = Field(
        None, description="Role IDs allowed to join games (empty = anyone)"
    )
    allowed_host_role_ids: list[str] | None = Field(
        None, description="Role IDs allowed to use this template (empty = anyone)"
    )

    # Pre-populated fields (host-editable defaults)
    max_players: int | None = Field(None, ge=1, le=100, description="Default max players")
    expected_duration_minutes: int | None = Field(
        None, ge=1, description="Default expected duration in minutes"
    )
    reminder_minutes: list[int] | None = Field(
        None, description="Default reminder times in minutes before game"
    )
    where: str | None = Field(None, max_length=500, description="Default location/platform")
    signup_instructions: str | None = Field(
        None, max_length=1000, description="Default signup instructions"
    )

    # Signup method configuration
    allowed_signup_methods: list[str] | None = Field(
        None, description="Allowed signup methods (empty/null = all methods allowed)"
    )
    default_signup_method: str | None = Field(
        None,
        description="Default signup method (must be in allowed list if both specified)",
    )


class TemplateUpdateRequest(BaseModel):
    """Update game template (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=4000)
    order: int | None = Field(None, ge=0)
    is_default: bool | None = None

    # Locked fields
    channel_id: str | None = None
    notify_role_ids: list[str] | None = None
    allowed_player_role_ids: list[str] | None = None
    allowed_host_role_ids: list[str] | None = None

    # Pre-populated fields
    max_players: int | None = Field(None, ge=1, le=100)
    expected_duration_minutes: int | None = Field(None, ge=1)
    reminder_minutes: list[int] | None = None
    where: str | None = Field(None, max_length=500)
    signup_instructions: str | None = Field(None, max_length=1000)

    # Signup method configuration
    allowed_signup_methods: list[str] | None = None
    default_signup_method: str | None = None


class TemplateResponse(BaseModel):
    """Template response with full details."""

    id: str = Field(..., description="Template UUID")
    guild_id: str = Field(..., description="Guild UUID")
    name: str = Field(..., description="Template name")
    description: str | None = Field(None, description="Template description")
    order: int = Field(..., description="Sort order")
    is_default: bool = Field(..., description="Whether this is the default template")

    # Locked fields
    channel_id: str = Field(..., description="Channel UUID")
    channel_name: str = Field(..., description="Channel name (resolved from Discord)")
    notify_role_ids: list[str] | None = Field(
        None, description="Role IDs to notify when game is created"
    )
    allowed_player_role_ids: list[str] | None = Field(
        None, description="Role IDs allowed to join games"
    )
    allowed_host_role_ids: list[str] | None = Field(
        None, description="Role IDs allowed to use this template"
    )

    # Pre-populated fields
    max_players: int | None = Field(None, description="Default max players")
    expected_duration_minutes: int | None = Field(None, description="Default expected duration")
    reminder_minutes: list[int] | None = Field(None, description="Default reminder times")
    where: str | None = Field(None, description="Default location")
    signup_instructions: str | None = Field(None, description="Default signup instructions")

    # Signup method configuration
    allowed_signup_methods: list[str] | None = Field(
        None, description="Allowed signup methods (empty/null = all methods allowed)"
    )
    default_signup_method: str | None = Field(None, description="Default signup method")

    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")

    model_config = {"from_attributes": True}


class TemplateListItem(BaseModel):
    """Template list item for display in template management."""

    id: str = Field(..., description="Template UUID")
    name: str = Field(..., description="Template name")
    description: str | None = Field(None, description="Template description")
    is_default: bool = Field(..., description="Whether this is the default template")
    channel_id: str = Field(..., description="Channel UUID")
    channel_name: str = Field(..., description="Channel name (resolved from Discord)")

    # Locked fields
    notify_role_ids: list[str] | None = Field(None, description="Roles to notify")
    allowed_player_role_ids: list[str] | None = Field(None, description="Allowed player roles")
    allowed_host_role_ids: list[str] | None = Field(None, description="Allowed host roles")

    # Pre-populated fields for display
    max_players: int | None = Field(None, description="Maximum players")
    expected_duration_minutes: int | None = Field(None, description="Expected duration")
    reminder_minutes: list[int] | None = Field(None, description="Reminder minutes")
    where: str | None = Field(None, description="Location")
    signup_instructions: str | None = Field(None, description="Signup instructions")

    # Signup method configuration
    allowed_signup_methods: list[str] | None = Field(None, description="Allowed signup methods")
    default_signup_method: str | None = Field(None, description="Default signup method")

    model_config = {"from_attributes": True}


class TemplateReorderRequest(BaseModel):
    """Bulk reorder templates."""

    template_orders: list[dict[str, int]] = Field(
        ..., description="List of {template_id: order} mappings"
    )
