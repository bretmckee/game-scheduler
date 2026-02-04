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


"""Pydantic schemas for Channel configuration."""

from pydantic import BaseModel, Field


class ChannelConfigCreateRequest(BaseModel):
    """Create channel configuration."""

    guild_id: str = Field(..., description="Parent guild ID (UUID)")
    channel_id: str = Field(..., description="Discord channel snowflake ID")
    is_active: bool = Field(
        default=True, description="Whether game posting is enabled in this channel"
    )


class ChannelConfigUpdateRequest(BaseModel):
    """Update channel configuration (all fields optional)."""

    is_active: bool | None = None


class ChannelConfigResponse(BaseModel):
    """Channel configuration response."""

    id: str = Field(..., description="Internal channel config ID (UUID)")
    guild_id: str = Field(..., description="Parent guild ID (UUID)")
    guild_discord_id: str = Field(..., description="Discord guild snowflake ID")
    channel_id: str = Field(..., description="Discord channel snowflake ID")
    channel_name: str = Field(..., description="Discord channel name")
    is_active: bool = Field(..., description="Whether channel is active for games")
    created_at: str = Field(..., description="Creation timestamp (UTC ISO)")
    updated_at: str = Field(..., description="Last update timestamp (UTC ISO)")

    model_config = {"from_attributes": True}
