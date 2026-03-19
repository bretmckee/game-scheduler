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


"""add_message_refresh_queue

Revision ID: b1d2e3f4a5c6
Revises: a7c1e3b4f9c2
Create Date: 2026-03-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic_utils.pg_function import PGFunction
from sqlalchemy import text as sql_text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1d2e3f4a5c6"
down_revision: str | None = "a7c1e3b4f9c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_refresh_queue",
        sa.Column(
            "id",
            sa.String(length=36),
            server_default=sa.text("gen_random_uuid()::text"),
            nullable=False,
        ),
        sa.Column("game_id", sa.String(length=36), nullable=False),
        sa.Column("channel_id", sa.String(length=20), nullable=False),
        sa.Column(
            "enqueued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["game_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_message_refresh_queue_channel_enqueued",
        "message_refresh_queue",
        ["channel_id", "enqueued_at"],
        unique=False,
    )

    notify_message_refresh_queue_changed = PGFunction(
        schema="public",
        signature="notify_message_refresh_queue_changed()",
        definition=(
            "RETURNS TRIGGER AS $$\n"
            "    BEGIN\n"
            "        PERFORM pg_notify(\n"
            "            'message_refresh_queue_changed',\n"
            "            NEW.channel_id::text\n"
            "        );\n"
            "        RETURN NEW;\n"
            "    END;\n"
            "    $$ LANGUAGE plpgsql"
        ),
    )
    op.create_entity(notify_message_refresh_queue_changed)

    op.execute(
        sql_text(
            """
        CREATE TRIGGER message_refresh_queue_trigger
        AFTER INSERT ON message_refresh_queue
        FOR EACH ROW
        EXECUTE FUNCTION notify_message_refresh_queue_changed()
    """
        )
    )


def downgrade() -> None:
    op.execute(
        sql_text("DROP TRIGGER IF EXISTS message_refresh_queue_trigger ON message_refresh_queue")
    )

    notify_message_refresh_queue_changed = PGFunction(
        schema="public",
        signature="notify_message_refresh_queue_changed()",
        definition=(
            "RETURNS TRIGGER AS $$\n"
            "    BEGIN\n"
            "        PERFORM pg_notify(\n"
            "            'message_refresh_queue_changed',\n"
            "            NEW.channel_id::text\n"
            "        );\n"
            "        RETURN NEW;\n"
            "    END;\n"
            "    $$ LANGUAGE plpgsql"
        ),
    )
    op.drop_entity(notify_message_refresh_queue_changed)

    op.drop_index(
        "ix_message_refresh_queue_channel_enqueued",
        table_name="message_refresh_queue",
    )
    op.drop_table("message_refresh_queue")
