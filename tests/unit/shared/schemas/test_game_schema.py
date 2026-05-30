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


"""Tests for game schema description length constraints."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shared.schemas.game import GameCreateRequest, GameResponse, GameUpdateRequest
from shared.schemas.participant import ParticipantResponse
from shared.utils.limits import MAX_DESCRIPTION_LENGTH

VALID_TEMPLATE_ID = "00000000-0000-0000-0000-000000000001"
VALID_SCHEDULED_AT = datetime(2026, 6, 1, 18, 0, 0, tzinfo=UTC)
VALID_HOST = ParticipantResponse(
    id="00000000-0000-0000-0000-000000000002",
    game_session_id="00000000-0000-0000-0000-000000000001",
    joined_at="2026-05-30T00:00:00+00:00",
    position_type=8000,
    position=0,
)


class TestGameCreateRequestDescriptionLimit:
    """Tests for GameCreateRequest description max_length=MAX_DESCRIPTION_LENGTH."""

    def test_description_at_limit_accepted(self):
        """Test that a 2,000-character description is accepted."""
        req = GameCreateRequest(
            template_id=VALID_TEMPLATE_ID,
            title="Test Game",
            scheduled_at=VALID_SCHEDULED_AT,
            description="A" * MAX_DESCRIPTION_LENGTH,
        )
        assert len(req.description) == MAX_DESCRIPTION_LENGTH

    def test_description_over_limit_rejected(self):
        """Test that a 2,001-character description is rejected."""
        with pytest.raises(ValidationError):
            GameCreateRequest(
                template_id=VALID_TEMPLATE_ID,
                title="Test Game",
                scheduled_at=VALID_SCHEDULED_AT,
                description="A" * (MAX_DESCRIPTION_LENGTH + 1),
            )

    def test_none_description_accepted(self):
        """Test that None description is accepted."""
        req = GameCreateRequest(
            template_id=VALID_TEMPLATE_ID,
            title="Test Game",
            scheduled_at=VALID_SCHEDULED_AT,
        )
        assert req.description is None


class TestGameUpdateRequestDescriptionLimit:
    """Tests for GameUpdateRequest description max_length=MAX_DESCRIPTION_LENGTH."""

    def test_description_at_limit_accepted(self):
        """Test that a 2,000-character description is accepted."""
        req = GameUpdateRequest(description="A" * MAX_DESCRIPTION_LENGTH)
        assert len(req.description) == MAX_DESCRIPTION_LENGTH

    def test_description_over_limit_rejected(self):
        """Test that a 2,001-character description is rejected."""
        with pytest.raises(ValidationError):
            GameUpdateRequest(description="A" * (MAX_DESCRIPTION_LENGTH + 1))

    def test_none_description_accepted(self):
        """Test that None description is accepted."""
        req = GameUpdateRequest(description=None)
        assert req.description is None


class TestGameCreateRequestPostAt:
    """Tests for GameCreateRequest.post_at field."""

    def test_post_at_none_accepted(self):
        """post_at defaults to None."""
        req = GameCreateRequest(
            template_id=VALID_TEMPLATE_ID,
            title="Test Game",
            scheduled_at=VALID_SCHEDULED_AT,
        )
        assert req.post_at is None

    def test_post_at_datetime_accepted(self):
        """post_at accepts a datetime value."""
        post_at = datetime(2026, 5, 31, 12, 0, 0, tzinfo=UTC)
        req = GameCreateRequest(
            template_id=VALID_TEMPLATE_ID,
            title="Test Game",
            scheduled_at=VALID_SCHEDULED_AT,
            post_at=post_at,
        )
        assert req.post_at == post_at


class TestGameUpdateRequestPostAt:
    """Tests for GameUpdateRequest post_at and clear_post_at fields."""

    def test_post_at_defaults_to_none(self):
        """post_at defaults to None (meaning do not change)."""
        req = GameUpdateRequest()
        assert req.post_at is None

    def test_clear_post_at_defaults_to_false(self):
        """clear_post_at sentinel defaults to False."""
        req = GameUpdateRequest()
        assert req.clear_post_at is False

    def test_clear_post_at_true_accepted(self):
        """clear_post_at=True is accepted."""
        req = GameUpdateRequest(clear_post_at=True)
        assert req.clear_post_at is True


class TestGameResponsePostAt:
    """Tests for GameResponse.post_at field."""

    def test_post_at_none_serializes(self):
        """post_at=None is valid and serializes correctly."""
        response = GameResponse(
            id="00000000-0000-0000-0000-000000000001",
            title="Test Game",
            scheduled_at="2026-06-01T18:00:00+00:00",
            guild_id="g1",
            channel_id="c1",
            host=VALID_HOST,
            status="SCHEDULED",
            signup_method="SELF_SIGNUP",
            participant_count=0,
            created_at="2026-05-30T00:00:00+00:00",
            updated_at="2026-05-30T00:00:00+00:00",
            post_at=None,
        )
        assert response.post_at is None

    def test_post_at_iso_string_accepted(self):
        """post_at accepts an ISO 8601 string."""
        response = GameResponse(
            id="00000000-0000-0000-0000-000000000001",
            title="Test Game",
            scheduled_at="2026-06-01T18:00:00+00:00",
            guild_id="g1",
            channel_id="c1",
            host=VALID_HOST,
            status="SCHEDULED",
            signup_method="SELF_SIGNUP",
            participant_count=0,
            created_at="2026-05-30T00:00:00+00:00",
            updated_at="2026-05-30T00:00:00+00:00",
            post_at="2026-05-31T12:00:00+00:00",
        )
        assert response.post_at == "2026-05-31T12:00:00+00:00"
