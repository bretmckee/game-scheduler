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
    avatar_url: str | None = Field(
        None,
        description="Discord CDN avatar URL (None if no avatar)",
    )
    joined_at: str = Field(..., description="Join timestamp (UTC ISO)")
    position_type: int = Field(
        ..., description="Participant type (8000=host-added, 24000=self-added)"
    )
    position: int = Field(..., description="Priority within participant type")

    model_config = {"from_attributes": True}
