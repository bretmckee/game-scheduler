#!/usr/bin/env python3
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


"""RabbitMQ infrastructure initialization."""

import logging
import os
import time

import pika
from opentelemetry import trace
from pika.exceptions import AMQPConnectionError

from shared.messaging.infrastructure import (
    DEAD_LETTER_QUEUES,
    DLQ_BINDINGS,
    DLX_EXCHANGE,
    MAIN_EXCHANGE,
    PRIMARY_QUEUE_ARGUMENTS,
    PRIMARY_QUEUES,
    QUEUE_BINDINGS,
)

logger = logging.getLogger(__name__)


def wait_for_rabbitmq(rabbitmq_url: str, max_retries: int = 60, retry_delay: float = 1.0) -> None:
    """
    Wait for RabbitMQ to be ready to accept connections.

    Args:
        rabbitmq_url: RabbitMQ connection URL
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retry attempts in seconds

    Raises:
        RuntimeError: If RabbitMQ is not ready after max_retries
    """
    tracer = trace.get_tracer(__name__)
    logger.info("Waiting for RabbitMQ (max %s attempts)", max_retries)

    with tracer.start_as_current_span("init.wait_rabbitmq") as span:
        for attempt in range(1, max_retries + 1):
            try:
                connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
                connection.close()
                logger.info("RabbitMQ is ready")
                span.set_status(trace.Status(trace.StatusCode.OK))
                return
            except AMQPConnectionError as e:
                if attempt < max_retries:
                    logger.debug(
                        "RabbitMQ not ready (attempt %s/%s): %s",
                        attempt,
                        max_retries,
                        e,
                    )
                    time.sleep(retry_delay)
                else:
                    error_msg = f"RabbitMQ failed to become ready after {max_retries} attempts"
                    logger.error(error_msg)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
                    span.record_exception(e)
                    raise RuntimeError(error_msg) from e


def create_infrastructure(rabbitmq_url: str) -> None:
    """
    Create RabbitMQ exchanges, queues, and bindings.

    All operations are idempotent - safe to run multiple times.

    Args:
        rabbitmq_url: RabbitMQ connection URL

    Raises:
        RuntimeError: If infrastructure creation fails
    """
    tracer = trace.get_tracer(__name__)
    logger.info("Creating RabbitMQ infrastructure")

    with tracer.start_as_current_span("init.rabbitmq_infrastructure") as span:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            channel = connection.channel()

            channel.exchange_declare(exchange=MAIN_EXCHANGE, exchange_type="topic", durable=True)
            logger.info("Declared exchange: %s", MAIN_EXCHANGE)

            channel.exchange_declare(exchange=DLX_EXCHANGE, exchange_type="topic", durable=True)
            logger.info("Declared dead letter exchange: %s", DLX_EXCHANGE)

            for dlq_name in DEAD_LETTER_QUEUES:
                channel.queue_declare(queue=dlq_name, durable=True)
                logger.info("Declared dead letter queue: %s", dlq_name)

            for dlq_name, routing_key in DLQ_BINDINGS:
                channel.queue_bind(exchange=DLX_EXCHANGE, queue=dlq_name, routing_key=routing_key)
                logger.info(
                    "Bound DLQ %s to %s with routing key %s",
                    dlq_name,
                    DLX_EXCHANGE,
                    routing_key,
                )

            for queue_name in PRIMARY_QUEUES:
                channel.queue_declare(
                    queue=queue_name, durable=True, arguments=PRIMARY_QUEUE_ARGUMENTS
                )
                logger.info("Declared primary queue: %s", queue_name)

            for queue_name, routing_key in QUEUE_BINDINGS:
                channel.queue_bind(
                    exchange=MAIN_EXCHANGE, queue=queue_name, routing_key=routing_key
                )
                logger.info(
                    "Bound queue %s to %s with routing key %s",
                    queue_name,
                    MAIN_EXCHANGE,
                    routing_key,
                )

            connection.close()
            logger.info("RabbitMQ infrastructure creation completed")
            span.set_status(trace.Status(trace.StatusCode.OK))

        except Exception as e:
            error_msg = "RabbitMQ infrastructure creation failed"
            logger.error("%s: %s", error_msg, e, exc_info=True)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            span.record_exception(e)
            raise RuntimeError(error_msg) from e


def initialize_rabbitmq() -> None:
    """
    Initialize RabbitMQ infrastructure (wait + create).

    Raises:
        RuntimeError: If RabbitMQ initialization fails
    """
    rabbitmq_url = os.getenv("RABBITMQ_URL")
    if not rabbitmq_url:
        error_msg = "RABBITMQ_URL environment variable not set"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    wait_for_rabbitmq(rabbitmq_url)
    create_infrastructure(rabbitmq_url)
    logger.info("RabbitMQ initialization completed successfully")


if __name__ == "__main__":
    """
    Standalone execution for CI/CD workflows.

    When run directly, initializes OpenTelemetry and executes RabbitMQ
    initialization independently of the full environment initialization.
    """
    import sys

    from shared.telemetry import flush_telemetry, init_telemetry

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    init_telemetry("init-service")

    try:
        initialize_rabbitmq()
        sys.exit(0)
    except Exception as e:
        logger.error("RabbitMQ initialization failed: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        flush_telemetry()
