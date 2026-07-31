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


"""SQL for backfilling game_templates rows to the signup-method/priority-role invariant.

Shared between the Alembic migration that applies this once in upgrade() and
the integration test that exercises it directly, so the two can't drift.
"""

BACKFILL_NO_PRIORITY_ROLES_SQL = """
    UPDATE game_templates
    SET
        allowed_signup_methods = CASE
            WHEN allowed_signup_methods IS NULL
                THEN '["SELF_SIGNUP", "HOST_SELECTED", "HOST_SELECTED_WITH_WAITLIST"]'::json
            WHEN (allowed_signup_methods::jsonb - 'ROLE_BASED') = '[]'::jsonb
                THEN '["SELF_SIGNUP", "HOST_SELECTED", "HOST_SELECTED_WITH_WAITLIST"]'::json
            ELSE (allowed_signup_methods::jsonb - 'ROLE_BASED')::json
        END,
        default_signup_method = CASE
            WHEN default_signup_method = 'ROLE_BASED' THEN NULL
            ELSE default_signup_method
        END
    WHERE signup_priority_role_ids IS NULL
       OR signup_priority_role_ids::jsonb = '[]'::jsonb
"""

BACKFILL_HAS_PRIORITY_ROLES_SQL = """
    UPDATE game_templates
    SET
        default_signup_method = 'ROLE_BASED',
        allowed_signup_methods = '["ROLE_BASED"]'::json
    WHERE signup_priority_role_ids IS NOT NULL
      AND signup_priority_role_ids::jsonb != '[]'::jsonb
"""
