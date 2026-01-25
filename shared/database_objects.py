# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""
PostgreSQL database objects (functions, triggers, indexes).

This module defines database-level objects that need to be tracked by Alembic
but are not part of SQLAlchemy model definitions. Using alembic-utils ensures
these objects are properly managed during migrations.
"""

from alembic_utils.pg_function import PGFunction
from alembic_utils.pg_trigger import PGTrigger

# Database function used by notification_schedule table to notify daemon of changes
notify_schedule_changed_function = PGFunction(
    schema="public",
    signature="notify_schedule_changed()",
    definition="""
    RETURNS TRIGGER AS $$
    BEGIN
        -- Only notify if change affects near-term schedule (within 10 minutes)
        -- This reduces noise for distant future notifications
        IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') AND
           NEW.notification_time <= NOW() + INTERVAL '10 minutes' AND
           NEW.sent = FALSE THEN
            PERFORM pg_notify(
                'notification_schedule_changed',
                json_build_object(
                    'operation', TG_OP,
                    'game_id', NEW.game_id::text,
                    'notification_time', NEW.notification_time::text
                )::text
            );
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
)

# Database trigger that invokes notify_schedule_changed on notification_schedule changes
notification_schedule_trigger = PGTrigger(
    schema="public",
    signature="notification_schedule_trigger",
    on_entity="public.notification_schedule",
    definition="""
    AFTER INSERT OR UPDATE OR DELETE
    FOR EACH ROW
    EXECUTE FUNCTION notify_schedule_changed()
    """,
)

# Database function used by game_status_schedule table to notify daemon of changes
notify_game_status_schedule_changed_function = PGFunction(
    schema="public",
    signature="notify_game_status_schedule_changed()",
    definition="""
    RETURNS TRIGGER AS $$
    BEGIN
        -- Always notify on INSERT/UPDATE/DELETE so daemon can wake immediately
        -- This enables true event-driven architecture without polling
        IF TG_OP = 'DELETE' THEN
            PERFORM pg_notify(
                'game_status_schedule_changed',
                json_build_object(
                    'operation', TG_OP,
                    'schedule_id', OLD.id::text,
                    'game_id', OLD.game_id::text
                )::text
            );
            RETURN OLD;
        ELSE
            -- INSERT or UPDATE
            IF NEW.executed = FALSE THEN
                PERFORM pg_notify(
                    'game_status_schedule_changed',
                    json_build_object(
                        'operation', TG_OP,
                        'schedule_id', NEW.id::text,
                        'game_id', NEW.game_id::text,
                        'transition_time', NEW.transition_time::text
                    )::text
                );
            END IF;
            RETURN NEW;
        END IF;
    END;
    $$ LANGUAGE plpgsql
    """,
)

# Database trigger that invokes notify_game_status_schedule_changed on game_status_schedule changes
game_status_schedule_trigger = PGTrigger(
    schema="public",
    signature="game_status_schedule_trigger",
    on_entity="public.game_status_schedule",
    definition="""
    AFTER INSERT OR UPDATE OR DELETE
    FOR EACH ROW
    EXECUTE FUNCTION notify_game_status_schedule_changed()
    """,
)

# All database objects that should be tracked by Alembic
ALL_DATABASE_OBJECTS = [
    notify_schedule_changed_function,
    notification_schedule_trigger,
    notify_game_status_schedule_changed_function,
    game_status_schedule_trigger,
]
