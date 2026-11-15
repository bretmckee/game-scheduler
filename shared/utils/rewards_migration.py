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


"""SQL expressions for converting game_sessions.rewards between text and a JSON list.

Shared between the Alembic migration and the integration test that exercises it
directly, so the two can't drift. Both expressions reference a column named
``rewards``.
"""

# Postgres ALTER COLUMN ... USING expression: existing text becomes a single
# entry; NULL and whitespace-only values become NULL.
REWARDS_TEXT_TO_JSON_EXPR = r"""
    CASE
        WHEN rewards IS NULL OR btrim(rewards, E' \t\r\n') = '' THEN NULL
        ELSE json_build_array(rewards)
    END
"""

# USING expressions cannot contain subqueries, so the downgrade evaluates this
# in an UPDATE into a temporary text column. Entry boundaries are not preserved.
REWARDS_JSON_TO_TEXT_EXPR = r"""
    (SELECT string_agg(value, E'\n\n') FROM json_array_elements_text(rewards))
"""
