"""change notification_schedule id to string

Revision ID: 013_change_id_to_string
Revises: 012_add_notification_schedule
Create Date: 2025-11-28

Changes notification_schedule.id column from UUID to String(36) for consistency
with all other tables in the schema.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "013_change_id_to_string"
down_revision = "012_add_notification_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change notification_schedule.id from UUID to String(36)."""
    # Drop the existing constraint and column, then recreate
    op.execute("ALTER TABLE notification_schedule DROP CONSTRAINT notification_schedule_pkey")
    op.execute("ALTER TABLE notification_schedule ALTER COLUMN id TYPE VARCHAR(36)")
    op.execute(
        "ALTER TABLE notification_schedule ALTER COLUMN id SET DEFAULT "
        "substring(md5(random()::text || clock_timestamp()::text) from 1 for 8) || '-' || "
        "substring(md5(random()::text || clock_timestamp()::text) from 1 for 4) || '-4' || "
        "substring(md5(random()::text || clock_timestamp()::text) from 1 for 3) || '-' || "
        "substring(md5(random()::text || clock_timestamp()::text) from 1 for 4) || '-' || "
        "substring(md5(random()::text || clock_timestamp()::text) from 1 for 12)"
    )
    op.execute("ALTER TABLE notification_schedule ADD PRIMARY KEY (id)")


def downgrade() -> None:
    """Change notification_schedule.id back from String(36) to UUID."""
    op.execute("ALTER TABLE notification_schedule DROP CONSTRAINT notification_schedule_pkey")
    op.execute("ALTER TABLE notification_schedule ALTER COLUMN id TYPE UUID USING id::uuid")
    op.execute("ALTER TABLE notification_schedule ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE notification_schedule ADD PRIMARY KEY (id)")
