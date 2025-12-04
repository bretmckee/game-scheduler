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
Status transition daemon for database-backed event-driven game status updates.

Replaces polling-based Celery beat task with PostgreSQL LISTEN/NOTIFY
and MIN() query pattern for reliable, scalable game status transitions.
"""

import logging
import os
import signal
import time

from sqlalchemy.orm import Session

from shared.database import SyncSessionLocal
from shared.models import GameSession, GameStatusSchedule
from shared.models.base import utc_now

from .postgres_listener import PostgresNotificationListener
from .status_schedule_queries import get_next_due_transition, mark_transition_executed

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    shutdown_requested = True


class StatusTransitionDaemon:
    """
    Event-driven status transition scheduler daemon.

    Uses MIN() query pattern with PostgreSQL LISTEN/NOTIFY for
    efficient, scalable game status transitions.
    """

    def __init__(
        self,
        database_url: str,
        max_timeout: int = 900,
    ):
        """
        Initialize status transition daemon.

        Args:
            database_url: PostgreSQL connection string (psycopg2 format)
            max_timeout: Maximum seconds to wait between checks (default: 15 min)
        """
        self.database_url = database_url
        self.max_timeout = max_timeout

        self.listener: PostgresNotificationListener | None = None
        self.db: Session | None = None

    def connect(self) -> None:
        """Establish connections to PostgreSQL."""
        self.listener = PostgresNotificationListener(self.database_url)
        self.listener.connect()
        self.listener.listen("game_status_schedule_changed")

        self.db = SyncSessionLocal()

        logger.info("Status transition daemon connections established")

    def run(self) -> None:
        """
        Main daemon loop using simplified single-transition pattern.

        Algorithm:
        1. Query for next unexecuted transition
        2. If due now (or past due), process it immediately
        3. If in future, wait until buffer_seconds before due time
        4. On wake (due time, NOTIFY, or timeout), go back to step 1
        """
        logger.info("Starting status transition daemon")

        self.connect()

        while not shutdown_requested:
            try:
                self._process_loop_iteration()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception:
                logger.exception("Unexpected error in daemon loop")
                if self.db:
                    self.db.rollback()
                time.sleep(5)

        logger.info("Status transition daemon shutting down")
        self._cleanup()

    def _process_loop_iteration(self) -> None:
        """Process one iteration of the daemon loop."""
        if self.listener is None or self.db is None:
            raise RuntimeError("Daemon not properly initialized")

        try:
            next_transition = get_next_due_transition(self.db)
        except Exception as e:
            logger.warning(f"Database query failed ({e}), recreating session")
            self.db.close()
            self.db = SyncSessionLocal()
            next_transition = get_next_due_transition(self.db)

        if not next_transition:
            wait_time = self.max_timeout
            logger.info(f"No transitions scheduled, waiting {wait_time}s for events or timeout")
        else:
            time_until_due = (next_transition.transition_time - utc_now()).total_seconds()

            if time_until_due <= 0:
                # Transition is past due, process immediately
                self._process_transition(next_transition)
                return

            # Transition is in the future, wait until due time
            # Pass float directly to wait_for_notification to preserve fractional seconds
            wait_time = min(time_until_due, float(self.max_timeout))

            logger.info(f"Next transition due in {time_until_due:.1f}s, waiting {wait_time:.1f}s")

        received, payload = self.listener.wait_for_notification(timeout=wait_time)

        if received:
            logger.info(f"Woke up due to NOTIFY event: {payload}")
        elif wait_time >= self.max_timeout:
            logger.info(f"Woke up due to periodic check timeout ({self.max_timeout}s)")
        else:
            logger.info("Woke up due to transition due time")

    def _process_transition(self, transition: GameStatusSchedule) -> None:
        """
        Process a single status transition.

        Updates game status in database.

        Args:
            transition: Transition to process
        """
        if self.db is None:
            raise RuntimeError("Daemon not properly initialized")

        try:
            # Load game with relationships for event publishing
            game = self.db.query(GameSession).filter(GameSession.id == transition.game_id).first()

            if not game:
                logger.error(f"Game {transition.game_id} not found for transition {transition.id}")
                # Mark transition executed to avoid retry
                mark_transition_executed(self.db, transition.id)
                self.db.commit()
                return

            if game.status != "SCHEDULED":
                logger.warning(
                    f"Game {game.id} status is {game.status}, expected SCHEDULED. "
                    f"Skipping transition."
                )
                # Mark transition executed since game state doesn't match
                mark_transition_executed(self.db, transition.id)
                self.db.commit()
                return

            # Update game status
            current_time = utc_now()
            game.status = transition.target_status
            game.updated_at = current_time

            # Mark transition executed
            mark_transition_executed(self.db, transition.id)

            # Commit database changes
            self.db.commit()

            logger.info(f"Transitioned game {game.id} to {transition.target_status}")

        except Exception:
            logger.exception(
                f"Failed to process transition {transition.id} for game {transition.game_id}"
            )
            if self.db:
                self.db.rollback()

    def _cleanup(self) -> None:
        """Clean up connections."""
        if self.listener:
            self.listener.close()

        if self.db:
            self.db.close()

        logger.info("Status transition daemon cleanup complete")


def main() -> None:
    """Entry point for status transition daemon."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Use base database URL for raw psycopg2 connection (no driver specifier)
    from shared.database import BASE_DATABASE_URL

    daemon = StatusTransitionDaemon(database_url=BASE_DATABASE_URL)

    daemon.run()


if __name__ == "__main__":
    main()
