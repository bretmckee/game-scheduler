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


"""add_post_at_game_sessions

Revision ID: 20260530_add_post_at_game_sessions
Revises: 20260419_drop_user_display_names
Create Date: 2026-05-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260530_add_post_at_game_sessions"
down_revision: str | None = "20260419_drop_user_display_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGGER_FUNC = """
CREATE OR REPLACE FUNCTION notify_game_announcement_changed()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.post_at IS NOT NULL THEN
        IF (TG_OP = 'INSERT') OR (OLD.post_at IS DISTINCT FROM NEW.post_at) THEN
            PERFORM pg_notify('game_announcement_changed', NEW.id);
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
"""

_TRIGGER = """
CREATE TRIGGER game_sessions_announcement_notify
AFTER INSERT OR UPDATE ON game_sessions
FOR EACH ROW EXECUTE FUNCTION notify_game_announcement_changed();
"""


def upgrade() -> None:
    """Add post_at column and NOTIFY trigger to game_sessions."""
    op.add_column(
        "game_sessions",
        sa.Column("post_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(_TRIGGER_FUNC)
    op.execute(_TRIGGER)


def downgrade() -> None:
    """Remove post_at column and NOTIFY trigger from game_sessions."""
    op.execute("DROP TRIGGER IF EXISTS game_sessions_announcement_notify ON game_sessions")
    op.execute("DROP FUNCTION IF EXISTS notify_game_announcement_changed()")
    op.drop_column("game_sessions", "post_at")
