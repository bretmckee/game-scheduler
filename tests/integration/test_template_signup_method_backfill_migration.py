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


"""Integration tests for the signup-method/priority-role backfill migration SQL.

The migration (alembic/versions/bf79aeffb6b0_backfill_template_signup_method_.py)
only ever runs once, against whatever data was in the database at that point in
time -- by the time these tests run, the migration has already executed against
an empty table, so it can't be re-triggered through `alembic upgrade`. These
tests instead execute the exact same SQL constants the migration runs (imported
from shared.utils.template_signup_method_backfill, not copy-pasted) against
manually inserted "pre-fix" rows, to verify the backfill logic itself is correct.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from shared.utils.template_signup_method_backfill import (
    BACKFILL_HAS_PRIORITY_ROLES_SQL,
    BACKFILL_NO_PRIORITY_ROLES_SQL,
)

pytestmark = pytest.mark.integration


def _insert_template(
    admin_db_sync,
    guild_id: str,
    channel_id: str,
    *,
    signup_priority_role_ids: list[str] | None,
    allowed_signup_methods: list[str] | None,
    default_signup_method: str | None,
) -> str:
    template_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_templates "
            "(id, guild_id, channel_id, name, max_players, "
            "signup_priority_role_ids, allowed_signup_methods, default_signup_method, "
            "created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :name, :max_players, "
            ":signup_priority_role_ids, :allowed_signup_methods, :default_signup_method, "
            ":created_at, :updated_at)"
        ),
        {
            "id": template_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "name": f"Backfill Test {template_id}",
            "max_players": 4,
            "signup_priority_role_ids": (
                json.dumps(signup_priority_role_ids)
                if signup_priority_role_ids is not None
                else None
            ),
            "allowed_signup_methods": (
                json.dumps(allowed_signup_methods) if allowed_signup_methods is not None else None
            ),
            "default_signup_method": default_signup_method,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()
    return template_id


def _fetch_template(admin_db_sync, template_id: str):
    result = admin_db_sync.execute(
        text(
            "SELECT signup_priority_role_ids, allowed_signup_methods, default_signup_method "
            "FROM game_templates WHERE id = :id"
        ),
        {"id": template_id},
    )
    return result.fetchone()


def _run_backfill(admin_db_sync) -> None:
    admin_db_sync.execute(text(BACKFILL_NO_PRIORITY_ROLES_SQL))
    admin_db_sync.execute(text(BACKFILL_HAS_PRIORITY_ROLES_SQL))
    admin_db_sync.commit()


@pytest.mark.parametrize(
    (
        "signup_priority_role_ids",
        "allowed_signup_methods",
        "default_signup_method",
        "expected_allowed",
        "expected_default",
    ),
    [
        pytest.param(
            None,
            None,
            None,
            ["SELF_SIGNUP", "HOST_SELECTED", "HOST_SELECTED_WITH_WAITLIST"],
            None,
            id="no_roles_null_fields_get_explicit_non_role_based_list",
        ),
        pytest.param(
            None,
            None,
            "ROLE_BASED",
            ["SELF_SIGNUP", "HOST_SELECTED", "HOST_SELECTED_WITH_WAITLIST"],
            None,
            id="no_roles_stale_role_based_default_is_cleared",
        ),
        pytest.param(
            [],
            None,
            None,
            ["SELF_SIGNUP", "HOST_SELECTED", "HOST_SELECTED_WITH_WAITLIST"],
            None,
            id="empty_role_list_treated_same_as_null",
        ),
        pytest.param(
            None,
            ["ROLE_BASED", "SELF_SIGNUP"],
            "SELF_SIGNUP",
            ["SELF_SIGNUP"],
            "SELF_SIGNUP",
            id="no_roles_role_based_stripped_from_mixed_allowed_list",
        ),
        pytest.param(
            None,
            ["ROLE_BASED"],
            "ROLE_BASED",
            ["SELF_SIGNUP", "HOST_SELECTED", "HOST_SELECTED_WITH_WAITLIST"],
            None,
            id="no_roles_allowed_list_of_only_role_based_falls_back_to_default_list",
        ),
        pytest.param(
            None,
            ["SELF_SIGNUP", "HOST_SELECTED"],
            "HOST_SELECTED",
            ["SELF_SIGNUP", "HOST_SELECTED"],
            "HOST_SELECTED",
            id="no_roles_already_valid_restriction_is_left_untouched",
        ),
        pytest.param(
            ["role-1", "role-2"],
            None,
            None,
            ["ROLE_BASED"],
            "ROLE_BASED",
            id="has_roles_null_fields_forced_to_role_based",
        ),
        pytest.param(
            ["role-1"],
            ["SELF_SIGNUP"],
            "SELF_SIGNUP",
            ["ROLE_BASED"],
            "ROLE_BASED",
            id="has_roles_stale_non_role_based_fields_overwritten",
        ),
        pytest.param(
            ["role-1"],
            ["ROLE_BASED"],
            "ROLE_BASED",
            ["ROLE_BASED"],
            "ROLE_BASED",
            id="has_roles_already_correct_is_idempotent",
        ),
    ],
)
def test_backfill_normalizes_template_row(
    admin_db_sync,
    create_guild,
    create_channel,
    signup_priority_role_ids,
    allowed_signup_methods,
    default_signup_method,
    expected_allowed,
    expected_default,
):
    """Backfill SQL normalizes a pre-existing row to the new invariant."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])

    template_id = _insert_template(
        admin_db_sync,
        guild["id"],
        channel["id"],
        signup_priority_role_ids=signup_priority_role_ids,
        allowed_signup_methods=allowed_signup_methods,
        default_signup_method=default_signup_method,
    )

    _run_backfill(admin_db_sync)

    row = _fetch_template(admin_db_sync, template_id)
    assert row is not None
    assert row.allowed_signup_methods == expected_allowed
    assert row.default_signup_method == expected_default
