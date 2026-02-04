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


"""Channel configuration service for create and update operations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.channel import ChannelConfiguration


async def create_channel_config(
    db: AsyncSession,
    guild_id: str,
    channel_discord_id: str,
    **settings: Any,  # noqa: ANN401
) -> ChannelConfiguration:
    """
    Create new channel configuration.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild_id: Parent guild configuration ID (UUID)
        channel_discord_id: Discord channel snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created channel configuration
    """
    channel_config = ChannelConfiguration(
        guild_id=guild_id,
        channel_id=channel_discord_id,
        **settings,
    )
    db.add(channel_config)
    await db.flush()
    return channel_config


async def update_channel_config(
    channel_config: ChannelConfiguration,
    **updates: Any,  # noqa: ANN401
) -> ChannelConfiguration:
    """
    Update channel configuration.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        channel_config: Existing channel configuration
        **updates: Fields to update (only non-None values are applied)

    Returns:
        Updated channel configuration
    """
    for key, value in updates.items():
        if value is not None:
            setattr(channel_config, key, value)

    return channel_config
