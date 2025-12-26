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


"""Shared fixtures for integration tests."""

import os

import pika
import pytest


@pytest.fixture(scope="module")
def rabbitmq_url():
    """Get RabbitMQ URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


@pytest.fixture
def rabbitmq_connection(rabbitmq_url):
    """Create RabbitMQ connection for test setup/assertions."""
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    yield connection
    connection.close()


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    """Create RabbitMQ channel for test operations."""
    channel = rabbitmq_connection.channel()
    yield channel
    channel.close()
