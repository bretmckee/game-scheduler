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


"""
Guild isolation middleware using ContextVars and SQLAlchemy event listeners.

Provides transparent guild-level data filtering for multi-tenant security.
"""

import logging
from contextvars import ContextVar

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import SessionTransaction

logger = logging.getLogger(__name__)

_current_guild_ids: ContextVar[list[str] | None] = ContextVar("current_guild_ids", default=None)


def set_current_guild_ids(guild_ids: list[str]) -> None:
    """
    Set guild IDs for current request context.

    Args:
        guild_ids: List of Discord guild IDs (snowflakes)
    """
    _current_guild_ids.set(guild_ids)


def get_current_guild_ids() -> list[str] | None:
    """
    Get guild IDs for current request context.

    Returns:
        List of guild IDs or None if not set
    """
    return _current_guild_ids.get(None)


def clear_current_guild_ids() -> None:
    """Clear guild IDs from current request context."""
    _current_guild_ids.set(None)


@event.listens_for(AsyncSession.sync_session_class, "after_begin")
def set_rls_context_on_transaction_begin(
    _session: Session, _transaction: SessionTransaction, connection: Connection
) -> None:
    """
    Automatically set PostgreSQL RLS context when transaction begins.

    Reads guild_ids from ContextVar and sets PostgreSQL session variable
    for use by RLS policies. Transaction-scoped (SET LOCAL).

    Args:
        _session: SQLAlchemy session (unused, required by event signature)
        _transaction: Current transaction (unused, required by event signature)
        connection: Database connection
    """
    guild_ids = get_current_guild_ids()

    if guild_ids is None or not guild_ids:
        return

    guild_ids_str = ",".join(guild_ids)

    # Use connection.execute() with text() instead of exec_driver_sql()
    # This is async-compatible and doesn't cause greenlet errors
    connection.execute(text(f"SET LOCAL app.current_guild_ids = '{guild_ids_str}'"))
