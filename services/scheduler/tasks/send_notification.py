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


"""Task to send game reminder notifications to participants."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.scheduler.celery_app import app
from services.scheduler.services import notification_service as notif_service
from shared import database
from shared.models import game

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    max_retries=3,
    name="services.scheduler.tasks.send_notification.send_game_reminder_due",
)
def send_game_reminder_due(self, game_id_str: str, reminder_minutes: int):
    """
    Publish game reminder due event for bot service to handle participant notifications.

    Args:
        game_id_str: Game session UUID as string
        reminder_minutes: Minutes before game this reminder is for
    """
    game_id = uuid.UUID(game_id_str)

    logger.info(
        f"=== Executing game reminder task: game={game_id}, reminder={reminder_minutes}min ==="
    )

    with database.get_sync_db_session() as db:
        try:
            game_session = _get_game(db, game_id)
            if not game_session:
                logger.error(f"Game {game_id} not found in database")
                return {"status": "error", "reason": "game_not_found"}

            if game_session.status != "SCHEDULED":
                logger.info(
                    f"Game {game_id} status is {game_session.status}, skipping notification"
                )
                return {"status": "skipped", "reason": "game_not_scheduled"}

            notification_srv = notif_service.get_notification_service()

            logger.info(
                f"Publishing game reminder due event: game={game_id}, "
                f"reminder={reminder_minutes}min"
            )

            success = notification_srv.send_game_reminder_due(
                game_id=game_id,
                reminder_minutes=reminder_minutes,
            )

            if success:
                logger.info(f"Successfully published game reminder event for game {game_id}")
                return {"status": "success"}
            else:
                logger.error(f"Failed to publish game reminder event for game {game_id}")
                raise Exception("Failed to publish game reminder event")

        except Exception as e:
            logger.error(
                f"Error in game reminder task: game={game_id}, error={e}",
                exc_info=True,
            )
            if self.request.retries < self.max_retries:
                retry_countdown = 60 * (self.request.retries + 1)
                logger.info(f"Retrying in {retry_countdown} seconds")
                raise self.retry(exc=e, countdown=retry_countdown) from e
            return {"status": "error", "reason": str(e)}


def _get_game(db: Session, game_id: uuid.UUID) -> game.GameSession | None:
    """Get game session by ID."""
    stmt = select(game.GameSession).where(game.GameSession.id == str(game_id))
    result = db.execute(stmt)
    return result.scalar_one_or_none()
