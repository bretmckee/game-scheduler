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


"""Tests for RabbitMQ consumer implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.messaging.consumer import EventConsumer


class TestEventConsumerConnectionFailures:
    """Test suite for EventConsumer connection failure scenarios."""

    @pytest.mark.asyncio
    async def test_bind_routing_key_connection_failure(self) -> None:
        """Test bind_routing_key raises RuntimeError when connection fails."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            consumer._queue = None

            with pytest.raises(
                RuntimeError, match="Queue connection failed: unable to bind routing key"
            ):
                await consumer.bind("test.routing.key")

    @pytest.mark.asyncio
    async def test_start_consuming_connection_failure(self) -> None:
        """Test start_consuming raises RuntimeError when connection fails."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            consumer._queue = None

            with pytest.raises(
                RuntimeError, match="Queue connection failed: unable to start consumer"
            ):
                await consumer.start_consuming()

    @pytest.mark.asyncio
    async def test_bind_routing_key_succeeds_after_reconnect(self) -> None:
        """Test bind_routing_key succeeds when connection is re-established."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        mock_queue = MagicMock()
        mock_queue.bind = AsyncMock()

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            consumer._queue = None
            mock_connect.side_effect = lambda: setattr(consumer, "_queue", mock_queue)
            mock_exchange = MagicMock()
            consumer._exchange = mock_exchange

            await consumer.bind("test.routing.key")

            mock_connect.assert_awaited_once()
            mock_queue.bind.assert_awaited_once_with(mock_exchange, routing_key="test.routing.key")

    @pytest.mark.asyncio
    async def test_start_consuming_succeeds_after_reconnect(self) -> None:
        """Test start_consuming succeeds when connection is re-established."""
        consumer = EventConsumer(
            queue_name="test_queue",
            exchange_name="test_exchange",
        )

        mock_queue = MagicMock()
        mock_queue.consume = AsyncMock()

        with patch.object(consumer, "connect", new_callable=AsyncMock) as mock_connect:
            consumer._queue = None
            mock_connect.side_effect = lambda: setattr(consumer, "_queue", mock_queue)

            await consumer.start_consuming()

            mock_connect.assert_awaited_once()
            mock_queue.consume.assert_awaited_once()
