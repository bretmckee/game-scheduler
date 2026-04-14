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


"""Unit tests for UserDisplayNameService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services import display_names as display_names_module
from services.api.services.user_display_names import UserDisplayNameService
from shared.models.user_display_name import UserDisplayName

GUILD_ID = "111222333"
USER_A = "100000001"
USER_B = "100000002"


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_resolver():
    return AsyncMock(spec=display_names_module.DisplayNameResolver)


@pytest.fixture
def service(mock_db, mock_resolver):
    return UserDisplayNameService(mock_db, mock_resolver)


def _make_row(user_id: str, guild_id: str, name: str, avatar: str | None = None) -> UserDisplayName:
    row = UserDisplayName()
    row.user_discord_id = user_id
    row.guild_discord_id = guild_id
    row.display_name = name
    row.avatar_url = avatar
    row.updated_at = datetime.now(UTC)
    return row


def _make_scalars_result(rows: list) -> MagicMock:
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    return result_mock


@pytest.mark.asyncio
async def test_resolve_db_hit_returns_without_calling_resolver(service, mock_db, mock_resolver):
    """DB hit: returns cached data without calling DisplayNameResolver."""
    row_a = _make_row(USER_A, GUILD_ID, "Alice", "https://cdn/alice.png")
    mock_db.execute = AsyncMock(return_value=_make_scalars_result([row_a]))

    result = await service.resolve(GUILD_ID, [USER_A])

    assert result == {USER_A: {"display_name": "Alice", "avatar_url": "https://cdn/alice.png"}}
    mock_resolver.resolve_display_names_and_avatars.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_db_miss_calls_resolver_and_upserts(service, mock_db, mock_resolver):
    """DB miss: falls through to DisplayNameResolver and upserts the result."""
    mock_db.execute = AsyncMock(return_value=_make_scalars_result([]))
    mock_resolver.resolve_display_names_and_avatars = AsyncMock(
        return_value={USER_B: {"display_name": "Bob", "avatar_url": None}}
    )

    result = await service.resolve(GUILD_ID, [USER_B])

    assert result == {USER_B: {"display_name": "Bob", "avatar_url": None}}
    mock_resolver.resolve_display_names_and_avatars.assert_awaited_once_with(GUILD_ID, [USER_B])
    mock_db.execute.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_mixed_hit_miss_only_missing_reach_resolver(service, mock_db, mock_resolver):
    """Mixed: only the missing user ID reaches DisplayNameResolver."""
    row_a = _make_row(USER_A, GUILD_ID, "Alice")
    mock_db.execute = AsyncMock(return_value=_make_scalars_result([row_a]))
    mock_resolver.resolve_display_names_and_avatars = AsyncMock(
        return_value={USER_B: {"display_name": "Bob", "avatar_url": None}}
    )

    result = await service.resolve(GUILD_ID, [USER_A, USER_B])

    assert USER_A in result
    assert result[USER_A]["display_name"] == "Alice"
    assert USER_B in result
    assert result[USER_B]["display_name"] == "Bob"
    # Only USER_B should have been sent to the resolver
    mock_resolver.resolve_display_names_and_avatars.assert_awaited_once_with(GUILD_ID, [USER_B])


@pytest.mark.asyncio
async def test_upsert_one_executes_merge(service, mock_db):
    """upsert_one writes the correct fields via DB execute."""
    mock_db.execute = AsyncMock()
    mock_db.flush = AsyncMock()

    await service.upsert_one(USER_A, GUILD_ID, "Alice Updated", "https://cdn/alice2.png")

    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_batch_empty_list_does_not_error(service, mock_db):
    """upsert_batch with empty list completes without error."""
    mock_db.execute = AsyncMock()
    mock_db.flush = AsyncMock()

    await service.upsert_batch([])

    mock_db.execute.assert_not_awaited()
