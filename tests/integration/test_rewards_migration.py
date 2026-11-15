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


"""Integration tests for the rewards text <-> JSON list migration SQL.

The migration converting game_sessions.rewards to a JSON list runs once, against
whatever data exists at upgrade time; by the time these tests run it has already
executed against an empty table. These tests execute the exact SQL expressions
the migration uses (imported from shared.utils.rewards_migration, not
copy-pasted) against literal pre-migration values to verify the conversion.
"""

import pytest
from sqlalchemy import text

from shared.utils.rewards_migration import (
    REWARDS_JSON_TO_TEXT_EXPR,
    REWARDS_TEXT_TO_JSON_EXPR,
)

pytestmark = pytest.mark.integration


def test_upgrade_expression_converts_text_to_single_entry_list(admin_db_sync):
    """Non-blank text becomes a one-entry list; NULL and blank text become NULL."""
    rows = admin_db_sync.execute(
        text(
            f"SELECT ord, {REWARDS_TEXT_TO_JSON_EXPR} AS converted "  # noqa: S608
            "FROM (VALUES (1, 'a'), (2, ''), (3, '  '), (4, NULL), "
            "(5, E'line1\\nline2'), (6, E' \\n\\t ')) AS t(ord, rewards) "
            "ORDER BY ord"
        )
    ).fetchall()

    assert [row.converted for row in rows] == [
        ["a"],
        None,
        None,
        None,
        ["line1\nline2"],
        None,
    ]


def test_downgrade_expression_joins_entries_with_blank_line(admin_db_sync):
    """A JSON list collapses to one text value with entries separated by a blank line."""
    rows = admin_db_sync.execute(
        text(
            f"SELECT ord, {REWARDS_JSON_TO_TEXT_EXPR} AS converted "  # noqa: S608
            "FROM (VALUES "
            '(1, CAST(\'["gold", "multi\\nline"]\' AS json)), '
            "(2, CAST('[\"solo\"]' AS json)), "
            "(3, CAST(NULL AS json)), "
            "(4, CAST('[]' AS json))"
            ") AS t(ord, rewards) "
            "ORDER BY ord"
        )
    ).fetchall()

    assert [row.converted for row in rows] == [
        "gold\n\nmulti\nline",
        "solo",
        None,
        None,
    ]
