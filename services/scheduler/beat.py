"""Celery beat scheduler entry point."""

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
    logger.info("Starting Celery beat scheduler")
    app.Beat().run()
