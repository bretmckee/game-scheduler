"""Celery worker entry point."""

import logging

from services.scheduler import config as scheduler_config
from services.scheduler.celery_app import app

config = scheduler_config.get_config()

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Starting Celery worker")
    app.worker_main(
        [
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--max-tasks-per-child=1000",
        ]
    )
