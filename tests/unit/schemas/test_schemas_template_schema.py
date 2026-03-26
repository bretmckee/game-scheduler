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


"""Tests for shared template schemas."""

import pytest
from pydantic import ValidationError

from shared.schemas import template as template_schemas


def test_template_create_request_allows_archive_fields():
    """Ensure archive fields are accepted on template creation."""
    request = template_schemas.TemplateCreateRequest(
        guild_id="guild-id",
        name="Template",
        channel_id="channel-id",
        archive_delay_seconds=0,
        archive_channel_id="archive-channel-id",
    )

    assert request.archive_delay_seconds == 0
    assert request.archive_channel_id == "archive-channel-id"


def test_template_response_includes_archive_fields():
    """Ensure archive fields are exposed on template responses."""
    response = template_schemas.TemplateResponse(
        id="template-id",
        guild_id="guild-id",
        name="Template",
        description=None,
        order=0,
        is_default=False,
        channel_id="channel-id",
        channel_name="channel-name",
        notify_role_ids=None,
        allowed_player_role_ids=None,
        allowed_host_role_ids=None,
        max_players=None,
        expected_duration_minutes=None,
        reminder_minutes=None,
        where=None,
        signup_instructions=None,
        allowed_signup_methods=None,
        default_signup_method=None,
        archive_delay_seconds=3600,
        archive_channel_id="archive-channel-id",
        archive_channel_name="archive-channel",
        created_at="2026-03-11T00:00:00",
        updated_at="2026-03-11T00:00:00",
    )

    assert response.archive_delay_seconds == 3600
    assert response.archive_channel_id == "archive-channel-id"
    assert response.archive_channel_name == "archive-channel"


def test_template_list_item_includes_archive_fields():
    """Ensure archive fields are exposed on template list items."""
    item = template_schemas.TemplateListItem(
        id="template-id",
        name="Template",
        description=None,
        is_default=False,
        channel_id="channel-id",
        channel_name="channel-name",
        notify_role_ids=None,
        allowed_player_role_ids=None,
        allowed_host_role_ids=None,
        max_players=None,
        expected_duration_minutes=None,
        reminder_minutes=None,
        where=None,
        signup_instructions=None,
        allowed_signup_methods=None,
        default_signup_method=None,
        archive_delay_seconds=None,
        archive_channel_id=None,
        archive_channel_name=None,
    )

    assert item.archive_delay_seconds is None
    assert item.archive_channel_id is None
    assert item.archive_channel_name is None


def test_signup_priority_role_ids_accepted_on_create():
    """signup_priority_role_ids up to 8 entries is accepted on create."""
    request = template_schemas.TemplateCreateRequest(
        guild_id="guild-id",
        name="Template",
        channel_id="channel-id",
        signup_priority_role_ids=["r1", "r2", "r3"],
    )
    assert request.signup_priority_role_ids == ["r1", "r2", "r3"]


def test_signup_priority_role_ids_max_8_enforced():
    """More than 8 signup_priority_role_ids raises a validation error."""
    with pytest.raises(ValidationError):
        template_schemas.TemplateCreateRequest(
            guild_id="guild-id",
            name="Template",
            channel_id="channel-id",
            signup_priority_role_ids=["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9"],
        )


def test_signup_priority_role_ids_max_8_enforced_on_update():
    """More than 8 signup_priority_role_ids raises a validation error on update too."""
    with pytest.raises(ValidationError):
        template_schemas.TemplateUpdateRequest(
            signup_priority_role_ids=["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9"],
        )


def test_template_response_includes_signup_priority_role_ids():
    """TemplateResponse exposes signup_priority_role_ids."""
    response = template_schemas.TemplateResponse(
        id="template-id",
        guild_id="guild-id",
        name="Template",
        description=None,
        order=0,
        is_default=False,
        channel_id="channel-id",
        channel_name="channel-name",
        notify_role_ids=None,
        allowed_player_role_ids=None,
        allowed_host_role_ids=None,
        signup_priority_role_ids=["role1"],
        max_players=None,
        expected_duration_minutes=None,
        reminder_minutes=None,
        where=None,
        signup_instructions=None,
        allowed_signup_methods=None,
        default_signup_method=None,
        archive_delay_seconds=None,
        archive_channel_id=None,
        archive_channel_name=None,
        created_at="2026-03-26T00:00:00",
        updated_at="2026-03-26T00:00:00",
    )
    assert response.signup_priority_role_ids == ["role1"]
