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


"""Unit tests for the join game bot handler."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from services.bot.handlers.join_game import _resolve_bot_role_position, _validate_join_game
from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod


def _make_game(priority_role_ids: list[str] | None = None) -> MagicMock:
    game = MagicMock()
    game.template = MagicMock()
    game.template.signup_priority_role_ids = priority_role_ids
    return game


def _make_game_no_template() -> MagicMock:
    game = MagicMock()
    game.template = None
    return game


def _make_role_checker() -> MagicMock:
    checker = MagicMock()
    checker.seed_user_roles = AsyncMock()
    return checker


def _make_db_scalar_result(value):
    """Return a mock db.execute() result with scalar_one_or_none() set."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


class TestValidateJoinGame:
    """Tests for _validate_join_game."""

    @pytest.mark.asyncio
    async def test_host_selected_rejects_self_join(self):
        """HOST_SELECTED games reject self-joins server-side.

        The Discord join button is disabled for HOST_SELECTED games, but that
        is client-side only; the handler must reject it too in case the
        button is bypassed (stale message, replayed interaction, etc.).
        """
        game = MagicMock()
        game.status = "SCHEDULED"
        game.signup_method = SignupMethod.HOST_SELECTED.value

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[_make_db_scalar_result(game)])

        result = await _validate_join_game(db, uuid.uuid4(), "discord-user-id")

        assert result["can_join"] is False
        assert "does not accept self-signups" in result["error"]


class TestResolveBotRolePosition:
    """Tests for _resolve_bot_role_position."""

    @pytest.mark.asyncio
    async def test_no_priority_roles_returns_self_added(self):
        """Empty priority list skips role resolution and returns SELF_ADDED."""
        interaction = MagicMock()
        game = _make_game(priority_role_ids=[])
        result = await _resolve_bot_role_position(interaction, game, _make_role_checker())
        assert result == (ParticipantType.SELF_ADDED, 32767)

    @pytest.mark.asyncio
    async def test_no_template_returns_self_added(self):
        """Missing template returns SELF_ADDED without error."""
        interaction = MagicMock()
        result = await _resolve_bot_role_position(
            interaction, _make_game_no_template(), _make_role_checker()
        )
        assert result == (ParticipantType.SELF_ADDED, 32767)

    @pytest.mark.asyncio
    async def test_non_member_interaction_returns_self_added(self):
        """DM / non-guild interaction (User, not Member) returns SELF_ADDED."""
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.User)  # not a Member
        game = _make_game(priority_role_ids=["role_a"])
        result = await _resolve_bot_role_position(interaction, game, _make_role_checker())
        assert result == (ParticipantType.SELF_ADDED, 32767)

    @pytest.mark.asyncio
    async def test_member_with_matching_role_returns_role_matched(self):
        """Guild member whose roles match the priority list gets ROLE_MATCHED."""
        guild_id = "999"
        role_a_id = "111"

        mock_role = MagicMock()
        mock_role.id = int(role_a_id)

        interaction = MagicMock()
        interaction.guild_id = int(guild_id)
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.id = 42
        interaction.user.roles = [mock_role]

        game = _make_game(priority_role_ids=[role_a_id])
        checker = _make_role_checker()

        result = await _resolve_bot_role_position(interaction, game, checker)

        assert result == (ParticipantType.ROLE_MATCHED, 0)
        checker.seed_user_roles.assert_called_once_with("42", guild_id, [role_a_id])

    @pytest.mark.asyncio
    async def test_everyone_role_excluded_from_user_roles(self):
        """The @everyone pseudo-role (same id as guild) is excluded from role IDs."""
        guild_id = "999"
        role_a_id = "111"

        everyone_role = MagicMock()
        everyone_role.id = int(guild_id)

        real_role = MagicMock()
        real_role.id = int(role_a_id)

        interaction = MagicMock()
        interaction.guild_id = int(guild_id)
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.id = 42
        interaction.user.roles = [everyone_role, real_role]

        game = _make_game(priority_role_ids=[role_a_id])
        checker = _make_role_checker()

        result = await _resolve_bot_role_position(interaction, game, checker)

        assert result == (ParticipantType.ROLE_MATCHED, 0)
        checker.seed_user_roles.assert_called_once_with("42", guild_id, [role_a_id])

    @pytest.mark.asyncio
    async def test_member_with_no_matching_role_returns_self_added(self):
        """Guild member whose roles don't match any priority role gets SELF_ADDED."""
        guild_id = "999"

        mock_role = MagicMock()
        mock_role.id = 777

        interaction = MagicMock()
        interaction.guild_id = int(guild_id)
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.id = 42
        interaction.user.roles = [mock_role]

        game = _make_game(priority_role_ids=["111", "222"])
        checker = _make_role_checker()

        result = await _resolve_bot_role_position(interaction, game, checker)

        assert result == (ParticipantType.SELF_ADDED, 32767)
        checker.seed_user_roles.assert_called_once_with("42", "999", ["777"])
