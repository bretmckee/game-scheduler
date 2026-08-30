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


"""Unit tests for the get_participant_seats route handler."""

import types
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status as http_status

from services.api.routes import games as games_routes
from shared.models.participant import ParticipantType

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
T1 = T0.replace(hour=13)
T2 = T0.replace(hour=14)
T3 = T0.replace(hour=15)


def _make_user(discord_id: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(discord_id=discord_id)


def _make_participant(
    participant_id: str,
    discord_id: str | None = None,
    display_name: str | None = None,
    position_type: int = ParticipantType.SELF_ADDED,
    position: int = 32767,
    joined_at: datetime = T0,
) -> types.SimpleNamespace:
    user = None if discord_id is None else _make_user(discord_id)
    return types.SimpleNamespace(
        id=f"pid-{participant_id}",
        game_session_id="game-1",
        user_id=None if user is None else f"uuid-{participant_id}",
        display_name=display_name,
        joined_at=joined_at,
        position_type=position_type,
        position=position,
        user=user,
    )


def _make_game(participants: list[types.SimpleNamespace], max_players: int = 2):
    game = MagicMock()
    game.host = _make_user("host-discord-id")
    game.guild = types.SimpleNamespace(guild_id="discord-guild-id")
    game.participants = participants
    game.max_players = max_players
    game.signup_method = "SELF_SIGNUP"
    game.guild_id = "db-guild-uuid"
    return game


def _make_current_user() -> MagicMock:
    user = MagicMock()
    user.user.discord_id = "user_discord_id"
    return user


class TestGetParticipantSeats:
    """Tests for host-facing participant seating endpoint."""

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self):
        """Missing game raises HTTP 404 before any authorization work."""
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await games_routes.get_participant_seats(
                game_id="missing",
                current_user=_make_current_user(),
                game_service=game_service,
                role_service=MagicMock(),
            )

        assert exc_info.value.status_code == http_status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_access_denial_propagates(self):
        """verify_game_access failures propagate to the caller unchanged."""
        game = _make_game([_make_participant("a", "user-a")])
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)
        denial = HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="no roles")

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new=AsyncMock(side_effect=denial),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await games_routes.get_participant_seats(
                game_id="game-1",
                current_user=_make_current_user(),
                game_service=game_service,
                role_service=MagicMock(),
            )

        assert exc_info.value is denial

    @pytest.mark.asyncio
    async def test_non_manager_returns_403(self):
        """Users who can view the game but not manage it are forbidden."""
        game = _make_game([_make_participant("a", "user-a")])
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                new_callable=AsyncMock,
                return_value=False,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await games_routes.get_participant_seats(
                game_id="game-1",
                current_user=_make_current_user(),
                game_service=game_service,
                role_service=MagicMock(),
            )

        assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN
        assert "host or a server manager" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_can_manage_http_exception_treated_as_forbidden(self):
        """A raising can_manage_game check degrades to 403 rather than 500."""
        game = _make_game([_make_participant("a", "user-a")])
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                side_effect=HTTPException(status_code=http_status.HTTP_404_NOT_FOUND),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await games_routes.get_participant_seats(
                game_id="game-1",
                current_user=_make_current_user(),
                game_service=game_service,
                role_service=MagicMock(),
            )

        assert exc_info.value.status_code == http_status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_manager_receives_real_user_seats_only_in_order(self):
        """Only linked users appear; placeholders are excluded and seats renumbered.

        Confirmed real users are numbered first (canonical order); waitlist
        numbering continues after them with no gaps left by placeholder slots.
        Names come from the primary-name resolver, never guild nicknames.
        """
        participants = [
            _make_participant(
                "b", "user-b", position_type=ParticipantType.HOST_ADDED, position=1, joined_at=T2
            ),
            # Placeholder inside the confirmed prefix must not consume a seat number
            _make_participant(
                "tbd-confirmed",
                display_name="TBD slot",
                position_type=ParticipantType.HOST_ADDED,
                position=2,
                joined_at=T2,
            ),
            _make_participant("c", "user-c", joined_at=T0),
            _make_participant(
                "a", "user-a", position_type=ParticipantType.HOST_ADDED, position=0, joined_at=T1
            ),
            # Distinct join time from user-c so overflow order never depends on stability
            _make_participant("tbd-overflow", display_name="Open Slot", joined_at=T3),
        ]
        # max_players=3 puts tbd-confirmed inside the confirmed window
        game = _make_game(participants, max_players=3)
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)

        mock_resolver = MagicMock()
        # Deliberately different values than any nickname to prove non-nick resolution
        mock_resolver.resolve_primary_names = AsyncMock(
            return_value={"user-a": "Bret", "user-b": "Beth", "user-c": "Casey"}
        )

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.api.routes.games.display_names_module.get_display_name_resolver",
                new_callable=AsyncMock,
                return_value=mock_resolver,
            ) as mock_get_resolver,
        ):
            result = await games_routes.get_participant_seats(
                game_id="game-1",
                current_user=_make_current_user(),
                game_service=game_service,
                role_service=MagicMock(),
            )

        assert [seat.position for seat in result.seats] == [1, 2, 3]
        assert [seat.discord_id for seat in result.seats] == ["user-a", "user-b", "user-c"]
        # a and b are host-added (confirmed); c is the first self-add (waitlist);
        # both placeholders are absent from the output entirely
        assert [(seat.name,) for seat in result.seats] == [
            ("Bret",),
            ("Beth",),
            ("Casey",),
        ]
        mock_resolver.resolve_primary_names.assert_awaited_once_with(
            "discord-guild-id", ["user-a", "user-b", "user-c"]
        )
        assert mock_get_resolver.await_count == 1

    @pytest.mark.asyncio
    async def test_placeholders_only_returns_empty_seats(self):
        """Games with no linked users return an empty list and never hit the resolver."""
        participants = [_make_participant("tbd", display_name="Open Slot")]
        game = _make_game(participants)
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "services.api.routes.games.display_names_module.get_display_name_resolver",
                new_callable=AsyncMock,
            ) as mock_get_resolver,
        ):
            result = await games_routes.get_participant_seats(
                game_id="game-1",
                current_user=_make_current_user(),
                game_service=game_service,
                role_service=MagicMock(),
            )

        assert result.seats == []
        mock_get_resolver.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_game_returns_no_seats(self):
        """A game with zero participants yields an empty seats list."""
        game = _make_game([])
        game_service = MagicMock()
        game_service.get_game = AsyncMock(return_value=game)

        with (
            patch(
                "services.api.routes.games.permissions_deps.verify_game_access",
                new_callable=AsyncMock,
            ),
            patch(
                "services.api.routes.games.permissions_deps.can_manage_game",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            result = await games_routes.get_participant_seats(
                game_id="game-1",
                current_user=_make_current_user(),
                game_service=game_service,
                role_service=MagicMock(),
            )

        assert result.seats == []
