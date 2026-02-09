# Copyright 2026 Bret McKee
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


# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""
Create default template for each guild after migration 019.

Run with: uv run python scripts/data_migration_create_default_templates.py

This script creates a default template for each guild that doesn't already have one.
It is idempotent and can be run multiple times safely.
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from shared import database, models


async def create_default_templates() -> None:
    """Create default template for each guild without one."""
    async with database.get_db_session() as db:
        # Get all guilds
        result = await db.execute(select(models.GuildConfiguration))
        guilds = result.scalars().all()

        for guild in guilds:
            # Check if default template already exists
            existing = await db.execute(
                select(models.GameTemplate).where(
                    models.GameTemplate.guild_id == guild.id,
                    models.GameTemplate.is_default.is_(True),
                )
            )
            if existing.scalar_one_or_none():
                print(f"Default template already exists for guild {guild.guild_id}")
                continue

            # Get first active channel, or any channel if none active
            channel_result = await db.execute(
                select(models.ChannelConfiguration)
                .where(models.ChannelConfiguration.guild_id == guild.id)
                .where(models.ChannelConfiguration.is_active.is_(True))
            )
            channel = channel_result.scalar_one_or_none()

            if not channel:
                # No active channel, get any channel
                channel_result = await db.execute(
                    select(models.ChannelConfiguration).where(
                        models.ChannelConfiguration.guild_id == guild.id
                    )
                )
                channel = channel_result.scalar_one_or_none()

            if not channel:
                print(f"No channels found for guild {guild.guild_id}, skipping")
                continue

            # Create default template
            template = models.GameTemplate(
                guild_id=guild.id,
                name="Default",
                description="Default game template",
                is_default=True,
                channel_id=channel.id,
                order=0,
                created_at=datetime.now(UTC).replace(tzinfo=None),
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(template)
            print(f"Created default template for guild {guild.guild_id}")

        await db.commit()
        print("Data migration complete!")


if __name__ == "__main__":
    asyncio.run(create_default_templates())
