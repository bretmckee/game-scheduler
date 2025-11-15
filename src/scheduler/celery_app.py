"""Celery application configuration."""

import logging

from celery import Celery

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "game-scheduler",
    broker="amqp://guest:guest@rabbitmq:5672/",
    backend="redis://redis:6379/1",
    include=["src.scheduler.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.scheduler.tasks.*": {"queue": "default"},
    },
)


if __name__ == "__main__":
    celery_app.start()
