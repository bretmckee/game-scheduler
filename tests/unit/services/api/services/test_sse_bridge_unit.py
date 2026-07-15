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


"""Tests for SSE bridge service."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from services.api.services.sse_bridge import SSEGameUpdateBridge, get_sse_bridge

_TEST_DB_URL = "postgresql+asyncpg://test:test@localhost/test_db"


@pytest.fixture
def sse_bridge():
    """Create SSE bridge instance for testing."""
    return SSEGameUpdateBridge(_TEST_DB_URL)


# ---------------------------------------------------------------------------
# Phase 4 xfail tests (RED) — asyncpg LISTEN migration
# ---------------------------------------------------------------------------


def test_bridge_accepts_db_url():
    """SSEGameUpdateBridge.__init__ accepts a db_url positional argument."""
    bridge = SSEGameUpdateBridge(_TEST_DB_URL)
    assert bridge._db_url == _TEST_DB_URL


@pytest.mark.asyncio
async def test_start_consuming_delegates_to_listen_with_reconnect():
    """start_consuming calls listen_with_reconnect with the URL, channel, and callback.

    Connection setup, retry-on-failure, and reconnect-after-disconnect behavior
    are the shared responsibility of listen_with_reconnect (see
    tests/unit/shared/test_pg_listen.py) — start_consuming only needs to prove
    it delegates to that helper with the right arguments.
    """
    bridge = SSEGameUpdateBridge(_TEST_DB_URL)

    with patch(
        "services.api.services.sse_bridge.listen_with_reconnect",
        new_callable=AsyncMock,
    ) as mock_listen:
        await bridge.start_consuming()

    args, kwargs = mock_listen.call_args
    assert args[0] == _TEST_DB_URL
    assert args[1] == "game_updated_sse"
    assert args[2] == bridge._on_notify
    assert kwargs["on_connected"] == bridge._set_conn
    assert kwargs["on_disconnected"] == bridge._clear_conn


@pytest.mark.asyncio
async def test_start_consuming_on_connected_and_on_disconnected_manage_conn():
    """The on_connected/on_disconnected hooks passed to listen_with_reconnect track _conn.

    This is what lets stop_consuming() close the live connection, and what
    lets a reconnect after a lost connection pick up a fresh one.
    """
    bridge = SSEGameUpdateBridge(_TEST_DB_URL)
    mock_conn = MagicMock()
    captured_kwargs: dict[str, object] = {}

    async def fake_listen(*_args: object, **kwargs: object) -> None:
        captured_kwargs.update(kwargs)

    with patch(
        "services.api.services.sse_bridge.listen_with_reconnect",
        side_effect=fake_listen,
    ):
        await bridge.start_consuming()

    captured_kwargs["on_connected"](mock_conn)  # type: ignore[operator]
    assert bridge._conn is mock_conn

    captured_kwargs["on_disconnected"]()  # type: ignore[operator]
    assert bridge._conn is None


def test_on_notify_ignores_invalid_json():
    """_on_notify drops payloads that are not valid JSON."""
    bridge = SSEGameUpdateBridge(_TEST_DB_URL)
    with patch.object(bridge, "_broadcast_to_clients") as mock_broadcast:
        bridge._on_notify(None, 0, "game_updated_sse", "not-json{{{")
    mock_broadcast.assert_not_called()


def test_on_notify_schedules_broadcast():
    """_on_notify parses JSON payload and schedules _broadcast_to_clients."""
    bridge = SSEGameUpdateBridge(_TEST_DB_URL)
    payload = json.dumps({"game_id": "g1", "guild_id": "guild1"})

    with patch.object(bridge, "_broadcast_to_clients") as mock_broadcast:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run_on_notify(bridge, payload))
        finally:
            loop.close()

    mock_broadcast.assert_called_once_with({"game_id": "g1", "guild_id": "guild1"})


async def _run_on_notify(bridge: SSEGameUpdateBridge, payload: str) -> None:
    bridge._on_notify(None, 0, "game_updated_sse", payload)
    await asyncio.sleep(0)


def test_on_notify_ignores_empty_payload():
    """_on_notify silently drops empty payload."""
    bridge = SSEGameUpdateBridge(_TEST_DB_URL)
    with patch.object(bridge, "_broadcast_to_clients") as mock_broadcast:
        bridge._on_notify(None, 0, "game_updated_sse", "")
    mock_broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_to_clients_accepts_dict():
    """_broadcast_to_clients accepts a dict payload from pg_notify."""
    bridge = SSEGameUpdateBridge(_TEST_DB_URL)
    client_queue: asyncio.Queue = asyncio.Queue()
    bridge.connections["c1"] = (client_queue, "session", "user123")

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = "123456789"
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock()

    mock_redis = AsyncMock()
    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch(
            "services.api.services.sse_bridge.cache_client.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "services.api.services.sse_bridge.member_projection.get_user_guilds",
            new=AsyncMock(return_value=["123456789"]),
        ),
    ):
        mock_tokens.return_value = {"access_token": "token"}
        await bridge._broadcast_to_clients({"game_id": str(uuid4()), "guild_id": "guild-uuid-1"})

    assert not client_queue.empty()
    mock_tokens.assert_called()


@pytest.fixture
def mock_db_session():
    """Create mock database session for testing."""
    mock_db = AsyncMock()
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = "123456789"  # Discord guild ID
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock()
    return mock_db


@pytest.fixture
def mock_event():
    """Create mock game.updated event as dict (pg_notify payload)."""
    return {
        "game_id": str(uuid4()),
        "guild_id": "123456789",
    }


@pytest.mark.asyncio
async def test_broadcast_filters_by_guild_membership(sse_bridge, mock_event, mock_db_session):
    """Test that events are only sent to users who are guild members."""
    client_queue = asyncio.Queue()
    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    mock_redis = AsyncMock()
    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db_session,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch(
            "services.api.services.sse_bridge.cache_client.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "services.api.services.sse_bridge.member_projection.get_user_guilds",
            new=AsyncMock(return_value=["123456789"]),
        ),
    ):
        mock_tokens.return_value = {"access_token": "token123"}

        await sse_bridge._broadcast_to_clients(mock_event)

        assert not client_queue.empty()
        message = await client_queue.get()
        data = json.loads(message)
        assert data["type"] == "game_updated"
        assert data["guild_id"] == "123456789"
        mock_tokens.assert_called()


@pytest.mark.asyncio
async def test_broadcast_skips_non_members(sse_bridge, mock_event, mock_db_session):
    """Test that events are not sent to non-guild members."""
    client_queue = asyncio.Queue()
    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    mock_redis = AsyncMock()
    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db_session,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch(
            "services.api.services.sse_bridge.cache_client.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "services.api.services.sse_bridge.member_projection.get_user_guilds",
            new=AsyncMock(return_value=["999999999"]),
        ),
    ):
        mock_tokens.return_value = {"access_token": "token123"}

        await sse_bridge._broadcast_to_clients(mock_event)

        assert client_queue.empty()
        mock_tokens.assert_called()


@pytest.mark.asyncio
async def test_broadcast_removes_disconnected_clients(sse_bridge, mock_event, mock_db_session):
    """Test that clients with expired sessions are removed."""
    client_queue = asyncio.Queue()
    session_token = "expired_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db_session,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
    ):
        mock_tokens.return_value = None

        await sse_bridge._broadcast_to_clients(mock_event)

        assert "client1" not in sse_bridge.connections
        mock_tokens.assert_called()


@pytest.mark.asyncio
async def test_broadcast_handles_full_queue(sse_bridge, mock_event, mock_db_session):
    """Test that events are dropped when client queue is full."""
    client_queue = asyncio.Queue(maxsize=1)
    await client_queue.put("existing_message")

    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    mock_redis = AsyncMock()
    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db_session,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch(
            "services.api.services.sse_bridge.cache_client.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "services.api.services.sse_bridge.member_projection.get_user_guilds",
            new=AsyncMock(return_value=["123456789"]),
        ),
    ):
        mock_tokens.return_value = {"access_token": "token123"}

        await sse_bridge._broadcast_to_clients(mock_event)

        assert client_queue.qsize() == 1
        assert await client_queue.get() == "existing_message"
        mock_tokens.assert_called()


@pytest.mark.asyncio
async def test_broadcast_handles_missing_guild_id(sse_bridge):
    """Test that events without guild_id are skipped."""
    data = {"game_id": str(uuid4())}

    client_queue = asyncio.Queue()
    sse_bridge.connections["client1"] = (client_queue, "session", "discord123")

    await sse_bridge._broadcast_to_clients(data)

    assert client_queue.empty()


@pytest.mark.asyncio
async def test_broadcast_handles_api_errors(sse_bridge, mock_event, mock_db_session):
    """Test that API errors during guild check don't crash the bridge."""
    client_queue = asyncio.Queue()
    session_token = "test_session"
    discord_id = "user123"

    sse_bridge.connections["client1"] = (client_queue, session_token, discord_id)

    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db_session,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
    ):
        mock_tokens.side_effect = Exception("API error")

        await sse_bridge._broadcast_to_clients(mock_event)

        assert "client1" in sse_bridge.connections
        assert client_queue.empty()
        mock_tokens.assert_called()


@pytest.mark.asyncio
async def test_stop_consuming_closes_asyncpg_conn(sse_bridge):
    """stop_consuming closes the asyncpg connection and clears _conn."""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    sse_bridge._conn = mock_conn

    await sse_bridge.stop_consuming()

    mock_conn.close.assert_called_once()
    assert sse_bridge._conn is None


@pytest.mark.asyncio
async def test_stop_consuming_handles_no_conn(sse_bridge):
    """stop_consuming works when no connection exists."""
    sse_bridge._conn = None
    await sse_bridge.stop_consuming()
    assert sse_bridge._conn is None


def test_get_sse_bridge_returns_singleton():
    """Test that get_sse_bridge returns the same instance."""
    bridge1 = get_sse_bridge()
    bridge2 = get_sse_bridge()
    assert bridge1 is bridge2


@pytest.mark.asyncio
async def test_broadcast_to_multiple_clients(sse_bridge, mock_event, mock_db_session):
    """Test broadcasting to multiple authorized clients."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()

    sse_bridge.connections["client1"] = (queue1, "session1", "user1")
    sse_bridge.connections["client2"] = (queue2, "session2", "user2")

    mock_redis = AsyncMock()
    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db_session,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch(
            "services.api.services.sse_bridge.cache_client.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "services.api.services.sse_bridge.member_projection.get_user_guilds",
            new=AsyncMock(return_value=["123456789"]),
        ),
    ):
        mock_tokens.return_value = {"access_token": "token123"}

        await sse_bridge._broadcast_to_clients(mock_event)

        assert not queue1.empty()
        assert not queue2.empty()

        message1 = json.loads(await queue1.get())
        message2 = json.loads(await queue2.get())

        assert message1["guild_id"] == "123456789"
        assert message2["guild_id"] == "123456789"
        mock_tokens.assert_called()


def test_set_keepalive_interval_validation():
    """Test keepalive interval configuration with validation."""
    bridge = get_sse_bridge()

    # Valid value should succeed
    bridge.set_keepalive_interval(5)
    assert bridge.keepalive_interval_seconds == 5

    # Zero should raise ValueError
    with pytest.raises(ValueError, match="Keepalive interval must be positive"):
        bridge.set_keepalive_interval(0)

    # Negative should raise ValueError
    with pytest.raises(ValueError, match="Keepalive interval must be positive"):
        bridge.set_keepalive_interval(-1)


@pytest.mark.asyncio
async def test_broadcast_uses_projection_not_oauth_for_guild_check(
    sse_bridge, mock_event, mock_db_session
):
    """Broadcast loop must use member_projection.get_user_guilds, not oauth2.get_user_guilds."""
    client_queue = asyncio.Queue()
    sse_bridge.connections["client1"] = (client_queue, "test_session", "user123")

    mock_redis = AsyncMock()

    with (
        patch(
            "services.api.services.sse_bridge.get_bypass_db_session",
            return_value=mock_db_session,
        ),
        patch("services.api.services.sse_bridge.tokens.get_user_tokens") as mock_tokens,
        patch(
            "services.api.services.sse_bridge.cache_client.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "services.api.services.sse_bridge.member_projection.get_user_guilds",
            new=AsyncMock(return_value=["123456789"]),
        ),
    ):
        mock_tokens.return_value = {"access_token": "token123", "is_maintainer": False}

        await sse_bridge._broadcast_to_clients(mock_event)

        assert not client_queue.empty(), (
            "Message must be delivered via projection-based guild check"
        )
        mock_tokens.assert_called()
