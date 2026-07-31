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


"""Structural sanity checks for the template signup-method backfill SQL.

The actual data-transform behavior is verified against real Postgres by
tests/integration/test_template_signup_method_backfill_migration.py. These
tests only guard against structural regressions (e.g. a renamed column or
table) that unit tests can catch without a database.
"""

from shared.utils.template_signup_method_backfill import (
    BACKFILL_HAS_PRIORITY_ROLES_SQL,
    BACKFILL_NO_PRIORITY_ROLES_SQL,
)


def test_no_priority_roles_sql_targets_game_templates_and_excludes_role_based():
    sql = BACKFILL_NO_PRIORITY_ROLES_SQL
    assert "UPDATE game_templates" in sql
    assert "signup_priority_role_ids" in sql
    assert "allowed_signup_methods" in sql
    assert "default_signup_method" in sql
    assert "ROLE_BASED" in sql
    assert "SELF_SIGNUP" in sql
    assert "HOST_SELECTED" in sql
    assert "HOST_SELECTED_WITH_WAITLIST" in sql


def test_has_priority_roles_sql_targets_game_templates_and_forces_role_based():
    sql = BACKFILL_HAS_PRIORITY_ROLES_SQL
    assert "UPDATE game_templates" in sql
    assert "signup_priority_role_ids" in sql
    assert "default_signup_method = 'ROLE_BASED'" in sql
    assert "allowed_signup_methods = '[\"ROLE_BASED\"]'::json" in sql


def test_backfill_statements_have_disjoint_where_clauses():
    """The two UPDATEs must partition rows by IS NULL vs IS NOT NULL so
    every row is touched by exactly one of them."""
    assert "signup_priority_role_ids IS NULL" in BACKFILL_NO_PRIORITY_ROLES_SQL
    assert "signup_priority_role_ids IS NOT NULL" in BACKFILL_HAS_PRIORITY_ROLES_SQL
