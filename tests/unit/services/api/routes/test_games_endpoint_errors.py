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


"""Unit tests for game endpoint error paths."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status as http_status

from services.api.routes import games as games_routes
from services.api.services import participant_resolver as resolver_module


@pytest.fixture
def mock_game_service():
    svc = AsyncMock()
    svc.db = AsyncMock()
    return svc


class TestCreateGame:
    @pytest.mark.asyncio
    async def test_create_game_validation_error(self, mock_current_user_unit, mock_game_service):
        mock_game_service.create_game.side_effect = resolver_module.ValidationError(
            invalid_mentions=["@ghost"], valid_participants=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.create_game(
                template_id="tmpl-1",
                title="Test Game",
                scheduled_at="2026-06-01T20:00:00Z",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=MagicMock(),
            )

        assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc_info.value.detail["error"] == "invalid_mentions"

    @pytest.mark.asyncio
    async def test_create_game_value_error_not_found(
        self, mock_current_user_unit, mock_game_service
    ):
        mock_game_service.create_game.side_effect = ValueError("Template not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.create_game(
                template_id="tmpl-1",
                title="Test Game",
                scheduled_at="2026-06-01T20:00:00Z",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=MagicMock(),
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_game_malformed_scheduled_at_raises_http_exception(
        self, mock_current_user_unit, mock_game_service
    ):
        """A malformed scheduled_at must produce a clean HTTPException, not crash.

        datetime.fromisoformat() raises ValueError before game_data is ever
        assigned, so the except clause's reference to game_data must not blow
        up with UnboundLocalError.
        """
        with pytest.raises(HTTPException) as exc_info:
            await games_routes.create_game(
                template_id="tmpl-1",
                title="Test Game",
                scheduled_at="not-a-date",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=MagicMock(),
            )

        assert isinstance(exc_info.value, HTTPException)
        assert exc_info.value.status_code >= http_status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_game_malformed_reminder_minutes_json_raises_http_exception(
        self, mock_current_user_unit, mock_game_service
    ):
        """Malformed JSON in reminder_minutes must not crash with UnboundLocalError.

        json.loads() raises json.JSONDecodeError (a ValueError subclass) before
        game_data is ever assigned.
        """
        with pytest.raises(HTTPException) as exc_info:
            await games_routes.create_game(
                template_id="tmpl-1",
                title="Test Game",
                scheduled_at="2026-06-01T20:00:00Z",
                reminder_minutes="not-json",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=MagicMock(),
            )

        assert isinstance(exc_info.value, HTTPException)
        assert exc_info.value.status_code >= http_status.HTTP_400_BAD_REQUEST


class TestListGames:
    @pytest.mark.asyncio
    async def test_list_games_filters_unauthorized_games(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game = MagicMock()
        mock_game_service.list_games.return_value = ([mock_game], 1)

        with patch(
            "services.api.dependencies.permissions.verify_game_access",
            side_effect=HTTPException(status_code=http_status.HTTP_403_FORBIDDEN),
        ):
            result = await games_routes.list_games(
                guild_id=None,
                channel_id=None,
                status=None,
                role=None,
                limit=25,
                offset=0,
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
                display_name_resolver=MagicMock(),
            )

        assert result.games == []
        assert result.total == 1  # DB pre-auth count is returned even when auth filters all games


class TestGetGame:
    @pytest.mark.asyncio
    async def test_get_game_can_manage_exception_defaults_false(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game = MagicMock()
        mock_game.guild = MagicMock()
        mock_game.guild.guild_id = "discord-guild-123"
        mock_game.host = MagicMock()
        mock_game.host.discord_id = "host-discord-123"
        mock_game_service.get_game.return_value = mock_game

        with (
            patch(
                "services.api.dependencies.permissions.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.dependencies.permissions.can_manage_game",
                side_effect=HTTPException(status_code=http_status.HTTP_403_FORBIDDEN),
            ),
            patch(
                "services.api.routes.games._build_game_response",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ) as mock_build,
        ):
            await games_routes.get_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        mock_build.assert_called_once_with(
            mock_game,
            can_manage=False,
        )


class TestUpdateGame:
    @pytest.mark.asyncio
    async def test_update_game_validation_error(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.update_game.side_effect = resolver_module.ValidationError(
            invalid_mentions=["@ghost"], valid_participants=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.update_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_game_value_error_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.update_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.update_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_game_malformed_scheduled_at_raises_http_exception(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        """A malformed scheduled_at must produce a clean HTTPException, not crash.

        _parse_update_form_data() raises ValueError via datetime.fromisoformat()
        before update_data is ever assigned, so the except clause's reference to
        update_data must not blow up with UnboundLocalError.
        """
        with pytest.raises(HTTPException) as exc_info:
            await games_routes.update_game(
                game_id="game-1",
                scheduled_at="not-a-date",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert isinstance(exc_info.value, HTTPException)
        assert exc_info.value.status_code >= http_status.HTTP_400_BAD_REQUEST


class TestDeleteGame:
    @pytest.mark.asyncio
    async def test_delete_game_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.delete_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.delete_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_game_forbidden(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.delete_game.side_effect = ValueError("You are not the host")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.delete_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_game_success_records_metric(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        """After a successful cancel, record_game_cancelled('api', ...) is called."""
        mock_game = MagicMock()
        mock_game.scheduled_at = datetime(2026, 7, 20, 18, 0, tzinfo=UTC)
        mock_game.expected_duration_minutes = 90
        mock_game_service.get_game.return_value = mock_game

        with patch("services.api.routes.games.record_game_cancelled") as mock_record:
            await games_routes.delete_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        mock_record.assert_called_once_with("api", mock_game.scheduled_at, 90)


class TestCloneGame:
    @pytest.mark.asyncio
    async def test_clone_game_validation_error(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        """clone_game's ValidationError path (widened error union) returns 422.

        Exercises resolver_module.ValidationError specifically, mirroring the
        create_game route's equivalent test -- previously only covered at
        the integration level for the clone endpoint.
        """
        mock_game_service.clone_game.side_effect = resolver_module.ValidationError(
            invalid_mentions=["@ghost"], valid_participants=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.clone_game(
                game_id="game-1",
                scheduled_at="2026-07-01T20:00:00Z",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc_info.value.detail["error"] == "invalid_mentions"

    @pytest.mark.asyncio
    async def test_clone_game_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.clone_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.clone_game(
                game_id="game-1",
                scheduled_at="2026-07-01T20:00:00Z",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_clone_game_forbidden(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        mock_game_service.clone_game.side_effect = ValueError("Not the host")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.clone_game(
                game_id="game-1",
                scheduled_at="2026-07-01T20:00:00Z",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_clone_game_malformed_scheduled_at_raises_http_exception(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        """A malformed scheduled_at must produce a clean HTTPException, not crash.

        datetime.fromisoformat() raises ValueError before clone_data is ever
        assigned, so the except clause's reference to clone_data must not blow
        up with UnboundLocalError.
        """
        with pytest.raises(HTTPException) as exc_info:
            await games_routes.clone_game(
                game_id="game-1",
                scheduled_at="not-a-date",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
            )

        assert isinstance(exc_info.value, HTTPException)
        assert exc_info.value.status_code >= http_status.HTTP_400_BAD_REQUEST


class TestJoinGame:
    @pytest.fixture
    def mock_game(self):
        game = MagicMock()
        game.guild_id = "guild-uuid-1"
        game.guild = MagicMock()
        game.guild.guild_id = "discord-guild-123"
        game.post_at = None
        game.message_id = None
        return game

    @pytest.mark.asyncio
    async def test_join_game_not_found(
        self, mock_current_user_unit, mock_game_service, mock_role_service, mock_game
    ):
        mock_game_service.get_game.return_value = mock_game
        mock_game_service.join_game.side_effect = ValueError("Game not found")

        with patch(
            "services.api.dependencies.permissions.verify_game_access",
            new_callable=AsyncMock,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await games_routes.join_game(
                    game_id="game-1",
                    current_user=mock_current_user_unit,
                    game_service=mock_game_service,
                    role_service=mock_role_service,
                    display_name_resolver=MagicMock(),
                )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_join_game_bad_request(
        self, mock_current_user_unit, mock_game_service, mock_role_service, mock_game
    ):
        mock_game_service.get_game.return_value = mock_game
        mock_game_service.join_game.side_effect = ValueError("Game is full")

        with patch(
            "services.api.dependencies.permissions.verify_game_access",
            new_callable=AsyncMock,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await games_routes.join_game(
                    game_id="game-1",
                    current_user=mock_current_user_unit,
                    game_service=mock_game_service,
                    role_service=mock_role_service,
                    display_name_resolver=MagicMock(),
                )

        assert exc_info.value.status_code == http_status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_join_game_returns_404_for_pre_announced_game(
        self, mock_current_user_unit, mock_game_service, mock_role_service
    ):
        """join_game returns 404 when game has a future post_at and no message_id."""
        mock_game = MagicMock()
        mock_game.post_at = datetime(2099, 1, 1, tzinfo=UTC).replace(tzinfo=None)
        mock_game.message_id = None
        mock_game_service.get_game.return_value = mock_game

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.join_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
                display_name_resolver=MagicMock(),
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_join_game_success_returns_resolved_display_name(
        self, mock_current_user_unit, mock_game_service, mock_role_service, mock_game
    ):
        """Successful join returns a ParticipantResponse with the guild display name."""
        mock_game.template = None
        mock_game_service.get_game.return_value = mock_game

        participant = MagicMock()
        participant.id = "participant-uuid-1"
        participant.game_session_id = "game-uuid-1"
        participant.user_id = "user-uuid-1"
        participant.user.discord_id = "discord-user-123"
        participant.display_name = "StoredName"
        participant.joined_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        participant.position_type = 24000
        participant.position = 0
        mock_game_service.join_game.return_value = participant

        mock_resolver = AsyncMock()
        mock_resolver.resolve_display_names_and_avatars.return_value = {
            "discord-user-123": {
                "display_name": "GuildDisplayName",
                "avatar_url": "https://cdn.discordapp.com/avatar.png",
            }
        }

        with (
            patch(
                "services.api.dependencies.permissions.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch("services.api.routes.games.record_game_joined") as mock_record,
        ):
            result = await games_routes.join_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
                role_service=mock_role_service,
                display_name_resolver=mock_resolver,
            )

        assert result.display_name == "GuildDisplayName"
        assert result.avatar_url == "https://cdn.discordapp.com/avatar.png"
        mock_record.assert_called_once_with("api")


class TestLeaveGame:
    @pytest.mark.asyncio
    async def test_leave_game_not_found(self, mock_current_user_unit, mock_game_service):
        mock_game_service.leave_game.side_effect = ValueError("Game not found")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.leave_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_leave_game_bad_request(self, mock_current_user_unit, mock_game_service):
        mock_game_service.leave_game.side_effect = ValueError("Not a participant")

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.leave_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
            )

        assert exc_info.value.status_code == http_status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_leave_game_success_records_metric(
        self, mock_current_user_unit, mock_game_service
    ):
        """After a successful leave, record_game_left('api') is called."""
        with patch("services.api.routes.games.record_game_left") as mock_record:
            await games_routes.leave_game(
                game_id="game-1",
                current_user=mock_current_user_unit,
                game_service=mock_game_service,
            )

        mock_record.assert_called_once_with("api")
