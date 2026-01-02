# Copyright 2026 Bret McKee (bret.mckee@gmail.com)
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


"""Integration tests for RLS context setting via event listener."""

import pytest
from sqlalchemy import text

from shared.data_access.guild_isolation import (
    clear_current_guild_ids,
    set_current_guild_ids,
)
from shared.database import get_db_session


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_listener_sets_rls_context_on_transaction_begin():
    """Event listener sets PostgreSQL session variable when transaction begins."""
    guild_ids = ["123456789", "987654321"]
    set_current_guild_ids(guild_ids)

    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT current_setting('app.current_guild_ids', true)")
        )
        rls_context = result.scalar_one()

        assert rls_context == "123456789,987654321"

        await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_listener_handles_empty_guild_list():
    """Event listener handles empty guild list gracefully."""
    set_current_guild_ids([])

    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT current_setting('app.current_guild_ids', true)")
        )
        rls_context = result.scalar_one()

        # Empty list treated same as None - variable not set
        assert rls_context in (None, "", "null")

        await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_listener_no_op_when_guild_ids_not_set():
    """Event listener skips RLS setup when ContextVar not set."""
    clear_current_guild_ids()

    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT current_setting('app.current_guild_ids', true)")
        )
        rls_context = result.scalar_one()

        # Setting returns NULL or empty string when not set
        assert rls_context in (None, "", "null")

        await session.commit()
