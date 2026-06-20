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


"""Unit tests for display_status computation in _build_game_response (Phase 11)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.routes.games import _build_game_response
from shared.models.participant import ParticipantType
from shared.schemas.participant import ParticipantResponse


def _make_host_response():
    return ParticipantResponse(
        id="host123",
        game_session_id="game123",
        user_id="host123",
        discord_id=None,
        display_name=None,
        avatar_url=None,
        joined_at="2026-01-01T00:00:00Z",
        position_type=ParticipantType.SELF_ADDED,
        position=0,
    )


def _make_game(*, status="SCHEDULED", recur_rule=None, post_at=None, message_id=None):
    """Return a minimal MagicMock game with configurable pending-confirmation fields."""
    game = MagicMock()
    game.id = "game123"
    game.participants = []
    game.max_players = 4
    game.where = None
    game.title = "Test Game"
    game.description = None
    game.signup_instructions = None
    game.guild_id = "guild123"
    game.channel_id = "channel123"
    game.message_id = message_id
    game.post_at = post_at
    game.reminder_minutes = None
    game.expected_duration_minutes = None
    game.notify_role_ids = None
    game.status = status
    game.signup_method = "SELF_SIGNUP"
    game.thumbnail_id = None
    game.banner_image_id = None
    game.rewards = None
    game.remind_host_rewards = False
    game.archive_channel_id = None
    game.recur_rule = recur_rule
    game.guild = None
    return game


_BUILD_PATCHES = [
    patch("services.api.routes.games.get_guild_channels_safe", new_callable=AsyncMock),
    patch("services.api.routes.games.channel_resolver_module.render_where_display"),
    patch("services.api.routes.games._build_host_response"),
    patch("services.api.routes.games._build_participant_responses"),
    patch("services.api.routes.games.participant_sorting.partition_participants"),
    patch("services.api.routes.games._fetch_discord_names", new_callable=AsyncMock),
    patch("services.api.routes.games._resolve_display_data", new_callable=AsyncMock),
    patch("services.api.routes.games.datetime_utils.format_datetime_as_utc"),
    patch("services.api.routes.games._render_text_fields", new_callable=AsyncMock),
]


async def _call_build_game_response(game):
    """Call _build_game_response with all collaborators patched to minimal stubs."""
    with (
        patch(
            "services.api.routes.games.get_guild_channels_safe",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "services.api.routes.games.channel_resolver_module.render_where_display",
            return_value=None,
        ),
        patch(
            "services.api.routes.games._build_host_response",
            return_value=_make_host_response(),
        ),
        patch(
            "services.api.routes.games._build_participant_responses",
            return_value=[],
        ),
        patch(
            "services.api.routes.games.participant_sorting.partition_participants",
            return_value=MagicMock(all_sorted=[], confirmed=[], overflow=[]),
        ),
        patch(
            "services.api.routes.games._fetch_discord_names",
            new_callable=AsyncMock,
            return_value=(None, None),
        ),
        patch(
            "services.api.routes.games._resolve_display_data",
            new_callable=AsyncMock,
            return_value=({}, None),
        ),
        patch(
            "services.api.routes.games.datetime_utils.format_datetime_as_utc",
            return_value="2026-01-01T00:00:00Z",
        ),
        patch(
            "services.api.routes.games._render_text_fields",
            new_callable=AsyncMock,
            return_value=("Test Game", None, None),
        ),
    ):
        return await _build_game_response(game)


class TestDisplayStatusComputation:
    """Tests that _build_game_response computes display_status correctly."""

    @pytest.mark.asyncio
    async def test_display_status_is_pending_confirmation_for_scheduled_recurrence_clone(
        self,
    ):
        """SCHEDULED clone with recur_rule, no post_at, no message_id → PENDING_CONFIRMATION."""
        game = _make_game(
            status="SCHEDULED",
            recur_rule="FREQ=WEEKLY;BYDAY=SA",
            post_at=None,
            message_id=None,
        )
        response = await _call_build_game_response(game)

        assert response.display_status == "PENDING_CONFIRMATION"

    @pytest.mark.asyncio
    async def test_display_status_is_scheduled_for_regular_game_without_recur_rule(self):
        """SCHEDULED game with no recur_rule → display_status is SCHEDULED."""
        game = _make_game(status="SCHEDULED", recur_rule=None, post_at=None, message_id=None)
        response = await _call_build_game_response(game)

        assert response.display_status == "SCHEDULED"

    @pytest.mark.asyncio
    async def test_display_status_is_scheduled_when_post_at_is_set(self):
        """SCHEDULED clone with recur_rule AND post_at set → display_status is SCHEDULED."""
        post_at_dt = MagicMock()
        game = _make_game(
            status="SCHEDULED",
            recur_rule="FREQ=WEEKLY;BYDAY=SA",
            post_at=post_at_dt,
            message_id=None,
        )
        response = await _call_build_game_response(game)

        assert response.display_status == "SCHEDULED"

    @pytest.mark.asyncio
    async def test_display_status_is_scheduled_when_message_id_is_set(self):
        """SCHEDULED clone with recur_rule AND message_id set → display_status is SCHEDULED."""
        game = _make_game(
            status="SCHEDULED",
            recur_rule="FREQ=WEEKLY;BYDAY=SA",
            post_at=None,
            message_id="1234567890",
        )
        response = await _call_build_game_response(game)

        assert response.display_status == "SCHEDULED"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["CANCELLED", "IN_PROGRESS", "COMPLETED"])
    async def test_display_status_passes_through_non_scheduled_statuses(self, status):
        """Non-SCHEDULED statuses pass through unchanged regardless of other fields."""
        game = _make_game(
            status=status,
            recur_rule="FREQ=WEEKLY;BYDAY=SA",
            post_at=None,
            message_id=None,
        )
        response = await _call_build_game_response(game)

        assert response.display_status == status
