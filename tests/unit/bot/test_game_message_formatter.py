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


"""Unit tests for GameMessageFormatter in services/bot/formatters/game_message.py."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import discord

# Initialize the full bot import chain before importing the formatter directly,
# to avoid the circular import that arises when formatters/__init__.py is loaded
# in isolation (formatters → views → events → formatters).
import services.bot.events.handlers  # noqa: F401
from services.bot.formatters.game_message import GameMessageFormatter
from shared.utils.limits import (
    DISCORD_EMBED_FIELD_VALUE_LIMIT,
    DISCORD_EMBED_TOTAL_SAFE_LIMIT,
)

_NOW = datetime(2026, 3, 21, 12, 0, 0, tzinfo=UTC)
_GAME_ID = "0b8f2a52-6a3e-4c1d-9a51-2f3c8e7d1a90"

_BASE_KWARGS = {
    "game_title": "Test Game",
    "description": "A fun game",
    "scheduled_at": _NOW,
    "host_id": "111222333444555666",
    "participant_ids": [],
    "overflow_ids": [],
    "current_count": 0,
    "max_players": 4,
    "status": "SCHEDULED",
    "game_id": _GAME_ID,
}


def _config():
    cfg = MagicMock()
    cfg.frontend_url = "https://example.com"
    cfg.backend_url = "https://api.example.com"
    return cfg


def test_create_game_embed_with_rewards_adds_spoiler_field():
    """Rewards field is added to the embed as a spoiler when rewards non-empty."""
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        embed = GameMessageFormatter.create_game_embed(
            **_BASE_KWARGS,
            rewards=["Gold coins for all"],
        )

    field_names = [f.name for f in embed.fields]
    field_values = [f.value for f in embed.fields]
    assert "🏆 Rewards" in field_names
    rewards_value = field_values[field_names.index("🏆 Rewards")]
    assert rewards_value == "||Gold coins for all||"


def test_create_game_embed_with_multiple_rewards_adds_one_field_per_entry():
    """Each reward gets its own spoiler field; only the first carries the heading."""
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        embed = GameMessageFormatter.create_game_embed(
            **_BASE_KWARGS,
            rewards=["Gold", "Sword\nof doom", "Shield"],
        )

    fields = [f for f in embed.fields if f.value and f.value.startswith("||")]
    assert [(f.name, f.value, f.inline) for f in fields] == [
        ("🏆 Rewards", "||Gold||", False),
        ("\u200b", "||Sword\nof doom||", False),
        ("\u200b", "||Shield||", False),
    ]


def test_create_game_embed_without_rewards_has_no_rewards_field():
    """No rewards field is added when rewards is None."""
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        embed = GameMessageFormatter.create_game_embed(**_BASE_KWARGS)

    field_names = [f.name for f in embed.fields]
    assert "🏆 Rewards" not in field_names


def test_create_game_embed_with_empty_list_rewards_has_no_rewards_field():
    """Empty rewards list is treated as falsy — no field added."""
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        embed = GameMessageFormatter.create_game_embed(
            **_BASE_KWARGS,
            rewards=[],
        )

    field_names = [f.name for f in embed.fields]
    assert "🏆 Rewards" not in field_names


_GAME_URL = f"https://example.com/games/{_GAME_ID}"
_REWARDS_LINK = f"[View rewards]({_GAME_URL})"
_MAX_INLINE_ENTRY = DISCORD_EMBED_FIELD_VALUE_LIMIT - len("||||")


def _rewards_embed(rewards: list[str], description: str = "A fun game") -> discord.Embed:
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        return GameMessageFormatter.create_game_embed(
            **{**_BASE_KWARGS, "description": description},
            rewards=rewards,
        )


def _reward_fields(embed: discord.Embed) -> list[tuple[str | None, str | None]]:
    """Return (name, value) of the rewards heading field and every field after it."""
    names = [f.name for f in embed.fields]
    start = names.index("🏆 Rewards")
    return [(f.name, f.value) for f in embed.fields[start:]]


def _base_embed(description: str = "A fun game") -> discord.Embed:
    with patch("services.bot.formatters.game_message.get_config", return_value=_config()):
        return GameMessageFormatter.create_game_embed(**{
            **_BASE_KWARGS,
            "description": description,
        })


def test_rewards_fit_inline_true_when_all_entries_fit():
    assert GameMessageFormatter._rewards_fit_inline(_base_embed(), ["Gold", "Sword"]) is True


def test_rewards_fit_inline_true_for_entry_at_field_value_limit():
    entry = "x" * _MAX_INLINE_ENTRY
    assert GameMessageFormatter._rewards_fit_inline(_base_embed(), [entry]) is True


def test_rewards_fit_inline_false_for_entry_over_field_value_limit():
    entry = "x" * (_MAX_INLINE_ENTRY + 1)
    assert GameMessageFormatter._rewards_fit_inline(_base_embed(), [entry]) is False


def test_rewards_fit_inline_false_when_field_count_exceeds_25():
    embed = _base_embed()
    rewards = ["r"] * (25 - len(embed.fields) + 1)
    assert GameMessageFormatter._rewards_fit_inline(embed, rewards) is False


def test_rewards_fit_inline_true_when_field_count_reaches_exactly_25():
    embed = _base_embed()
    rewards = ["r"] * (25 - len(embed.fields))
    assert GameMessageFormatter._rewards_fit_inline(embed, rewards) is True


def test_rewards_fit_inline_ignores_trimmable_description_length():
    embed = _base_embed(description="d" * 4000)
    rewards = ["x" * 1000, "y" * 1000]
    assert GameMessageFormatter._rewards_fit_inline(embed, rewards) is True


def test_rewards_fit_inline_false_when_rewards_alone_exceed_total_limit():
    rewards = ["x" * 1000] * 6
    assert GameMessageFormatter._rewards_fit_inline(_base_embed(), rewards) is False


def test_create_game_embed_oversize_entry_shows_single_link_field():
    embed = _rewards_embed(["Gold", "x" * (_MAX_INLINE_ENTRY + 1), "Shield"])

    assert _reward_fields(embed) == [("🏆 Rewards", _REWARDS_LINK)]
    assert not any(f.value and "Gold" in f.value for f in embed.fields)


def test_create_game_embed_too_many_fields_shows_single_link_field():
    embed = _rewards_embed(["r"] * 25)

    assert _reward_fields(embed) == [("🏆 Rewards", _REWARDS_LINK)]
    assert len(embed.fields) <= 25


def test_create_game_embed_total_length_overflow_shows_single_link_field():
    embed = _rewards_embed(["x" * 1000] * 6)

    assert _reward_fields(embed) == [("🏆 Rewards", _REWARDS_LINK)]
    assert len(embed) <= DISCORD_EMBED_TOTAL_SAFE_LIMIT


def test_create_game_embed_long_description_trimmed_instead_of_linking_rewards():
    description = "d" * 4000
    embed = _rewards_embed(["x" * 1000, "y" * 1000], description=description)

    assert _reward_fields(embed) == [
        ("🏆 Rewards", f"||{'x' * 1000}||"),
        ("\u200b", f"||{'y' * 1000}||"),
    ]
    assert embed.description is not None
    assert embed.description.endswith("...")
    assert len(embed.description) < len(description)
    assert len(embed) <= DISCORD_EMBED_TOTAL_SAFE_LIMIT
