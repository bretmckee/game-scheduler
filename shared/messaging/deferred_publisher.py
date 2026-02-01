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
Deferred event publisher for transactional event publishing.

Ensures events are published only after database transactions commit successfully,
preventing race conditions where consumers receive events for data not yet visible.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.messaging.events import Event, EventType
from shared.messaging.publisher import EventPublisher

logger = logging.getLogger(__name__)

_SESSION_INFO_KEY = "_deferred_events"


class DeferredEventPublisher:
    """
    Publisher that defers event publishing until transaction commit.

    Events are queued during transaction execution and published
    after successful commit via SQLAlchemy event listeners.
    On rollback, queued events are discarded.
    """

    def __init__(
        self,
        db: AsyncSession,
        event_publisher: EventPublisher,
    ) -> None:
        """
        Initialize deferred publisher.

        Args:
            db: Database session to attach deferred events to
            event_publisher: Underlying publisher for actual publishing
        """
        self.db = db
        self.event_publisher = event_publisher

    def publish_deferred(
        self,
        event: Event,
        routing_key: str | None = None,
    ) -> None:
        """
        Queue event for publishing after transaction commits.

        Args:
            event: Event to publish after commit
            routing_key: Optional routing key override
        """
        if _SESSION_INFO_KEY not in self.db.info:
            self.db.info[_SESSION_INFO_KEY] = []

        deferred_event = {
            "event": event,
            "routing_key": routing_key,
        }

        self.db.info[_SESSION_INFO_KEY].append(deferred_event)

        logger.debug(
            "Deferred event %s for publishing after commit (total queued: %d)",
            event.event_type,
            len(self.db.info[_SESSION_INFO_KEY]),
        )

    def publish_dict_deferred(
        self,
        event_type: str,
        data: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Queue event from dictionary data for publishing after commit.

        Args:
            event_type: Event type string
            data: Event payload
            trace_id: Optional correlation ID
        """
        event = Event(
            event_type=EventType(event_type),
            data=data,
            trace_id=trace_id,
        )

        self.publish_deferred(event)

    @staticmethod
    def get_deferred_events(session: AsyncSession | Session) -> list[dict[str, Any]]:
        """
        Get deferred events from session.

        Args:
            session: Database session (AsyncSession or Session)

        Returns:
            List of deferred event dictionaries
        """
        return session.info.get(_SESSION_INFO_KEY, [])

    @staticmethod
    def clear_deferred_events(session: AsyncSession | Session) -> None:
        """
        Clear deferred events from session.

        Args:
            session: Database session (AsyncSession or Session)
        """
        if _SESSION_INFO_KEY in session.info:
            del session.info[_SESSION_INFO_KEY]
            logger.debug("Cleared deferred events from session")
