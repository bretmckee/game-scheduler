"""Celery tasks for the scheduler service."""

import logging

from celery import current_app as celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def check_notifications() -> str:
    """Check for games that need notifications sent."""
    logger.info("Checking for games that need notifications...")
    # Placeholder implementation
    return "Notification check completed"


@celery_app.task
def send_notification(user_id: str, game_id: str, message: str) -> str:
    """Send notification to a user."""
    logger.info(f"Sending notification to user {user_id} for game {game_id}")
    # Placeholder implementation
    return f"Notification sent to {user_id}"
