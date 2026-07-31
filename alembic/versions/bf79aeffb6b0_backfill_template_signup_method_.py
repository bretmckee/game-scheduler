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


"""backfill_template_signup_method_priority_consistency

Revision ID: bf79aeffb6b0
Revises: 77f802eecfc5
Create Date: 2026-07-31 00:03:31.181420

"""

from collections.abc import Sequence

from alembic import op
from shared.utils.template_signup_method_backfill import (
    BACKFILL_HAS_PRIORITY_ROLES_SQL,
    BACKFILL_NO_PRIORITY_ROLES_SQL,
)

# revision identifiers, used by Alembic.
revision: str = "bf79aeffb6b0"
down_revision: str | None = "77f802eecfc5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Normalize existing game_templates rows to the new invariant.

    Before this release, allowed_signup_methods/default_signup_method had no
    template UI, so most rows have allowed_signup_methods = NULL. GameForm
    treats NULL/empty as "all methods allowed", which let ROLE_BASED appear
    as a selectable signup method on templates with no priority roles to
    resolve it. Backfill both directions of the new rule: priority roles
    imply ROLE_BASED, and no priority roles excludes ROLE_BASED.
    """
    op.execute(BACKFILL_NO_PRIORITY_ROLES_SQL)
    op.execute(BACKFILL_HAS_PRIORITY_ROLES_SQL)


def downgrade() -> None:
    """No-op: the prior state (which rows had NULL vs. an explicit list) isn't recoverable."""
