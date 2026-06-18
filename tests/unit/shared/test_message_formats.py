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


"""Unit tests for DMFormats and DMPredicates in shared/message_formats.py."""

from dataclasses import dataclass

from shared.message_formats import DMFormats, DMPredicates

# ---------------------------------------------------------------------------
# DMFormats.rewards_reminder
# ---------------------------------------------------------------------------


def test_rewards_reminder_contains_game_title():
    """Returned message includes the game title."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    assert "Epic Quest" in msg


def test_rewards_reminder_contains_edit_link():
    """Returned message includes the edit URL as a markdown link."""
    edit_url = "https://example.com/games/abc-123/edit"
    msg = DMFormats.rewards_reminder("Epic Quest", edit_url)
    assert edit_url in msg


def test_rewards_reminder_mentions_rewards():
    """Returned message references rewards."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    assert "rewards" in msg.lower()


def test_rewards_reminder_mentions_completed():
    """Returned message references game completion."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    assert "completed" in msg.lower()


# ---------------------------------------------------------------------------
# DMPredicates.rewards_reminder
# ---------------------------------------------------------------------------


@dataclass
class _DM:
    content: str | None


def test_rewards_reminder_predicate_matches_valid_dm():
    """Predicate matches a valid rewards reminder DM."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    predicate = DMPredicates.rewards_reminder("Epic Quest")
    assert predicate(_DM(msg)) is True


def test_rewards_reminder_predicate_rejects_wrong_title():
    """Predicate does not match when game title differs."""
    msg = DMFormats.rewards_reminder("Epic Quest", "https://example.com/edit")
    predicate = DMPredicates.rewards_reminder("Other Game")
    assert predicate(_DM(msg)) is False


def test_rewards_reminder_predicate_rejects_none_content():
    """Predicate returns False for None message content."""
    predicate = DMPredicates.rewards_reminder("Epic Quest")
    assert predicate(_DM(None)) is False


# ---------------------------------------------------------------------------
# DMFormats.reminder_participant
# ---------------------------------------------------------------------------

_UNIX = 1700000000
_JUMP_URL = "https://discord.com/channels/111/222/333"


def test_reminder_participant_contains_title():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, _JUMP_URL)
    assert "Epic Quest" in msg


def test_reminder_participant_contains_full_timestamp():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, _JUMP_URL)
    assert f"<t:{_UNIX}:F>" in msg


def test_reminder_participant_contains_relative_timestamp():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, _JUMP_URL)
    assert f"<t:{_UNIX}:R>" in msg


def test_reminder_participant_contains_jump_url():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, _JUMP_URL)
    assert _JUMP_URL in msg


def test_reminder_participant_no_jump_url_omits_link():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, None)
    assert "discord.com" not in msg
    assert f"<t:{_UNIX}:F>" in msg
    assert f"<t:{_UNIX}:R>" in msg


def test_reminder_participant_waitlist_prefix():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, True, None)
    assert "\U0001f3ab **[Waitlist]**" in msg


def test_reminder_participant_confirmed_no_waitlist_prefix():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, None)
    assert "Waitlist" not in msg


# ---------------------------------------------------------------------------
# DMFormats.reminder_host
# ---------------------------------------------------------------------------


def test_reminder_host_contains_title():
    msg = DMFormats.reminder_host("Epic Quest", _UNIX, _JUMP_URL)
    assert "Epic Quest" in msg


def test_reminder_host_contains_full_timestamp():
    msg = DMFormats.reminder_host("Epic Quest", _UNIX, _JUMP_URL)
    assert f"<t:{_UNIX}:F>" in msg


def test_reminder_host_contains_relative_timestamp():
    msg = DMFormats.reminder_host("Epic Quest", _UNIX, _JUMP_URL)
    assert f"<t:{_UNIX}:R>" in msg


def test_reminder_host_contains_jump_url():
    msg = DMFormats.reminder_host("Epic Quest", _UNIX, _JUMP_URL)
    assert _JUMP_URL in msg


def test_reminder_host_no_jump_url_omits_link():
    msg = DMFormats.reminder_host("Epic Quest", _UNIX, None)
    assert "discord.com" not in msg
    assert f"<t:{_UNIX}:F>" in msg


def test_reminder_host_prefix():
    msg = DMFormats.reminder_host("Epic Quest", _UNIX, None)
    assert "\U0001f3ae **[Host]**" in msg


# ---------------------------------------------------------------------------
# DMPredicates.reminder
# ---------------------------------------------------------------------------


def test_reminder_predicate_matches_participant_dm():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, _JUMP_URL)
    predicate = DMPredicates.reminder("Epic Quest")
    assert predicate(_DM(msg)) is True


def test_reminder_predicate_matches_host_dm():
    msg = DMFormats.reminder_host("Epic Quest", _UNIX, _JUMP_URL)
    predicate = DMPredicates.reminder("Epic Quest")
    assert predicate(_DM(msg)) is True


def test_reminder_predicate_matches_waitlist_dm():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, True, None)
    predicate = DMPredicates.reminder("Epic Quest")
    assert predicate(_DM(msg)) is True


def test_reminder_predicate_rejects_wrong_title():
    msg = DMFormats.reminder_participant("Epic Quest", _UNIX, False, None)
    predicate = DMPredicates.reminder("Other Game")
    assert predicate(_DM(msg)) is False


def test_reminder_predicate_rejects_none_content():
    predicate = DMPredicates.reminder("Epic Quest")
    assert predicate(_DM(None)) is False


# ---------------------------------------------------------------------------
# DMFormats.promotion
# ---------------------------------------------------------------------------


def test_promotion_no_jump_url_omits_link():
    msg = DMFormats.promotion("Epic Quest", _UNIX, jump_url=None)
    assert "discord.com" not in msg
    assert "Epic Quest" in msg


# ---------------------------------------------------------------------------
# DMFormats.join_with_instructions
# ---------------------------------------------------------------------------


def test_join_with_instructions_no_jump_url_omits_link():
    msg = DMFormats.join_with_instructions("Epic Quest", "Do the thing", _UNIX, jump_url=None)
    assert "discord.com" not in msg
    assert "Epic Quest" in msg


# ---------------------------------------------------------------------------
# DMFormats.join_simple
# ---------------------------------------------------------------------------


def test_join_simple_no_jump_url_omits_link():
    msg = DMFormats.join_simple("Epic Quest", jump_url=None)
    assert "discord.com" not in msg
    assert "Epic Quest" in msg


# ---------------------------------------------------------------------------
# DMFormats.join_waitlist and DMFormats.waitlist_demotion (TDD RED)
# ---------------------------------------------------------------------------


_JUMP_URL_GAME = "https://discord.com/channels/111/222/999"


def test_join_waitlist_contains_game_title():
    msg = DMFormats.join_waitlist("Epic Quest")
    assert "Epic Quest" in msg


def test_join_waitlist_contains_waitlist_text():
    msg = DMFormats.join_waitlist("Epic Quest")
    assert "joined" not in msg.lower()
    assert "waitlist" in msg.lower()


def test_join_waitlist_with_jump_url_includes_link():
    msg = DMFormats.join_waitlist("Epic Quest", jump_url=_JUMP_URL_GAME)
    assert _JUMP_URL_GAME in msg


def test_join_waitlist_without_jump_url_omits_link():
    msg = DMFormats.join_waitlist("Epic Quest", jump_url=None)
    assert "discord.com" not in msg
    assert "Epic Quest" in msg


# DMPredicates.join_waitlist


def test_join_waitlist_predicate_matches_waitlist_dm():
    msg = DMFormats.join_waitlist("Epic Quest")
    predicate = DMPredicates.join_waitlist("Epic Quest")
    assert predicate(_DM(msg)) is True


def test_join_waitlist_predicate_rejects_wrong_title():
    msg = DMFormats.join_waitlist("Epic Quest")
    predicate = DMPredicates.join_waitlist("Other Game")
    assert predicate(_DM(msg)) is False


def test_join_waitlist_predicate_rejects_none_content():
    predicate = DMPredicates.join_waitlist("Epic Quest")
    assert predicate(_DM(None)) is False


def test_waitlist_demotion_contains_game_title():
    msg = DMFormats.waitlist_demotion("Epic Quest")
    assert "Epic Quest" in msg


def test_waitlist_demotion_with_jump_url_includes_link():
    msg = DMFormats.waitlist_demotion("Epic Quest", jump_url=_JUMP_URL_GAME)
    assert _JUMP_URL_GAME in msg


# ---------------------------------------------------------------------------
# DMFormats.host_added_dropout and DMPredicates.host_added_dropout (TDD RED)
# ---------------------------------------------------------------------------


def test_host_added_dropout_contains_player_mention():
    msg = DMFormats.host_added_dropout("<@123456>", "Epic Quest", _UNIX)
    assert "<@123456>" in msg


def test_host_added_dropout_contains_game_title():
    msg = DMFormats.host_added_dropout("<@123456>", "Epic Quest", _UNIX)
    assert "Epic Quest" in msg


def test_host_added_dropout_contains_relative_timestamp():
    msg = DMFormats.host_added_dropout("<@123456>", "Epic Quest", _UNIX)
    assert f"<t:{_UNIX}:R>" in msg


def test_host_added_dropout_with_jump_url_includes_link():
    msg = DMFormats.host_added_dropout("<@123456>", "Epic Quest", _UNIX, jump_url=_JUMP_URL)
    assert _JUMP_URL in msg


def test_host_added_dropout_without_jump_url_omits_link():
    msg = DMFormats.host_added_dropout("<@123456>", "Epic Quest", _UNIX, jump_url=None)
    assert "discord.com" not in msg
    assert f"<t:{_UNIX}:R>" in msg


def test_host_added_dropout_predicate_matches():
    msg = DMFormats.host_added_dropout("<@123456>", "Epic Quest", _UNIX)
    predicate = DMPredicates.host_added_dropout("Epic Quest")
    assert predicate(_DM(msg)) is True


def test_host_added_dropout_predicate_rejects_wrong_title():
    msg = DMFormats.host_added_dropout("<@123456>", "Epic Quest", _UNIX)
    predicate = DMPredicates.host_added_dropout("Other Game")
    assert predicate(_DM(msg)) is False


def test_host_added_dropout_predicate_rejects_none_content():
    predicate = DMPredicates.host_added_dropout("Epic Quest")
    assert predicate(_DM(None)) is False


# ---------------------------------------------------------------------------
# DMFormats.recurrence_confirmation (TDD RED)
# ---------------------------------------------------------------------------

_NEXT_AT_UNIX = 1800000000


def test_recurrence_confirmation_contains_title():
    msg = DMFormats.recurrence_confirmation("Epic Quest", _NEXT_AT_UNIX)
    assert "Epic Quest" in msg


def test_recurrence_confirmation_contains_discord_timestamp():
    msg = DMFormats.recurrence_confirmation("Epic Quest", _NEXT_AT_UNIX)
    assert f"<t:{_NEXT_AT_UNIX}:F>" in msg


def test_recurrence_confirmation_mentions_confirmation_action():
    msg = DMFormats.recurrence_confirmation("Epic Quest", _NEXT_AT_UNIX)
    assert "confirm" in msg.lower()
