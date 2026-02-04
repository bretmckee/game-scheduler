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
