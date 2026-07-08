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


"""
PostgreSQL LISTEN/NOTIFY client for event-driven scheduler wake-ups.

Uses psycopg2 for synchronous LISTEN connections to receive real-time
notifications when the notification_schedule table changes.
"""

import json
import logging
import select
from typing import Any

import psycopg2
import psycopg2.extensions

logger = logging.getLogger(__name__)


class PostgresNotificationListener:
    """
    Synchronous PostgreSQL LISTEN/NOTIFY client for scheduler service.

    Establishes a dedicated connection for receiving NOTIFY events from
    PostgreSQL triggers. Uses select() for timeout-based waiting without
    blocking the main thread.
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize listener with database URL.

        Args:
            database_url: PostgreSQL connection string (plain format without driver specifier)
        """
        self.database_url = database_url
        self.conn: psycopg2.extensions.connection | None = None
        self._channels: set[str] = set()

    def connect(self) -> None:
        """
        Establish connection with autocommit for LISTEN.

        Raises:
            psycopg2.Error: If connection fails
        """
        if self.conn is not None and not self.conn.closed:
            logger.warning("Connection already established")
            return

        self.conn = psycopg2.connect(self.database_url)
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        if self._channels:
            for channel in self._channels:
                self._execute_listen(channel)

        logger.info("PostgreSQL LISTEN connection established")

    def _execute_listen(self, channel: str) -> None:
        """Execute LISTEN command on the connection."""
        if self.conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        with self.conn.cursor() as cursor:
            cursor.execute(f"LISTEN {channel};")
        logger.info("Listening on channel: %s", channel)

    def listen(self, channel: str) -> None:
        """
        Subscribe to notification channel.

        Args:
            channel: PostgreSQL notification channel name
        """
        if self.conn is None:
            msg = "Must call connect() before listen()"
            raise RuntimeError(msg)

        self._channels.add(channel)
        self._execute_listen(channel)

    def wait_for_notification(self, timeout: float) -> tuple[bool, dict[str, Any] | None]:
        """
        Wait for notification or timeout.

        Uses select() to wait for incoming notifications without blocking.
        Automatically parses JSON payloads from NOTIFY events.

        Args:
            timeout: Maximum seconds to wait for notification

        Returns:
            (received, payload) tuple:
            - received: True if notification received, False if timeout
            - payload: Parsed JSON payload if received, None otherwise

        Raises:
            RuntimeError: If not connected to database
        """
        if self.conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        if self.conn.closed:
            logger.warning("Connection closed, attempting reconnect")
            self.connect()

        if select.select([self.conn], [], [], timeout) == ([], [], []):
            return False, None

        self.conn.poll()

        if self.conn.notifies:
            notify = self.conn.notifies.pop(0)
            payload = None

            if notify.payload:
                try:
                    payload = json.loads(notify.payload)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse NOTIFY payload: %s", notify.payload)
                    payload = {"raw": notify.payload}

            logger.debug("Received NOTIFY on channel %s: %s", notify.channel, payload)
            return True, payload

        return False, None

    def close(self) -> None:
        """Close the connection."""
        if self.conn is not None and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL LISTEN connection closed")
