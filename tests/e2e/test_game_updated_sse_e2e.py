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


"""E2E test for SSE delivery after POST /api/v1/games/{id}/join.

Opens an SSE stream connection, calls POST /api/v1/games/{id}/join via the API,
and asserts that a game_updated event is received within the timeout window.

The API join path calls _publish_game_updated which fires
pg_notify('game_updated_sse', ...) → SSE bridge broadcasts → client receives event.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from tests.e2e.conftest import TimeoutType

pytestmark = pytest.mark.e2e


async def _consume_sse_game_updated(
    client: httpx.AsyncClient,
    game_id: str,
    events: list[dict],
    ready: asyncio.Event,
) -> None:
    """Stream SSE events until a game_updated event for game_id is received."""
    try:
        async with client.stream(
            "GET",
            "/api/v1/sse/game-updates",
            timeout=httpx.Timeout(timeout=30.0, connect=10.0),
        ) as response:
            ready.set()
            if response.status_code != 200:
                return
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "game_updated" and data.get("game_id") == game_id:
                    events.append(data)
                    return
    except Exception:
        ready.set()


@pytest.mark.asyncio
async def test_api_join_delivers_game_updated_sse_event(
    authenticated_admin_client,
    admin_db,
    synced_guild,
    test_timeouts,
):
    """
    POST /api/v1/games/{id}/join delivers a game_updated SSE event to a connected client.

    Verifies the full pg_notify → SSE bridge → SSE client delivery chain
    triggered by the API join path.
    """
    template_id = synced_guild.template_id
    scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    game_title = f"E2E SSE Join Test {uuid4().hex[:8]}"

    create_resp = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": template_id,
            "title": game_title,
            "scheduled_at": scheduled_at,
            "max_players": "4",
        },
    )
    assert create_resp.status_code == 201, f"Game create failed: {create_resp.text}"
    game_id = create_resp.json()["id"]

    received_events: list[dict] = []
    ready = asyncio.Event()

    consumer = asyncio.create_task(
        _consume_sse_game_updated(authenticated_admin_client, game_id, received_events, ready)
    )

    try:
        await asyncio.wait_for(ready.wait(), timeout=10.0)
        await asyncio.sleep(0.2)

        join_resp = await authenticated_admin_client.post(f"/api/v1/games/{game_id}/join")
        assert join_resp.status_code == 200, f"Join failed: {join_resp.text}"

        await asyncio.wait_for(consumer, timeout=test_timeouts[TimeoutType.DM_IMMEDIATE])
    finally:
        consumer.cancel()
        try:
            await consumer
        except (asyncio.CancelledError, Exception):
            pass

    assert len(received_events) >= 1, (
        f"No game_updated SSE event received for game_id={game_id} after join"
    )
    assert received_events[0]["game_id"] == game_id
