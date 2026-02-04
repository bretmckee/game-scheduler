# Copyright 2025-2026 Bret McKee
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


"""add_signup_methods

Revision ID: b49eb343d5a6
Revises: 8438728f8184
Create Date: 2025-12-27 12:50:58.193701

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b49eb343d5a6"
down_revision: str | None = "8438728f8184"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_templates",
        sa.Column("allowed_signup_methods", sa.JSON(), nullable=True),
    )
    op.add_column(
        "game_templates",
        sa.Column("default_signup_method", sa.String(length=50), nullable=True),
    )

    op.add_column(
        "game_sessions",
        sa.Column(
            "signup_method",
            sa.String(length=50),
            nullable=True,
            server_default="SELF_SIGNUP",
        ),
    )

    op.execute("UPDATE game_sessions SET signup_method = 'SELF_SIGNUP' WHERE signup_method IS NULL")

    op.alter_column("game_sessions", "signup_method", nullable=False)


def downgrade() -> None:
    op.drop_column("game_sessions", "signup_method")
    op.drop_column("game_templates", "default_signup_method")
    op.drop_column("game_templates", "allowed_signup_methods")
