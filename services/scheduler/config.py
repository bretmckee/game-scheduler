"""Scheduler service configuration."""

import os


class SchedulerConfig:
    """Configuration for scheduler service with Celery settings."""

    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/game_scheduler",
    )

    CELERY_BROKER_URL: str = RABBITMQ_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL

    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1

    CELERY_TASK_DEFAULT_RETRY_DELAY: int = 60
    CELERY_TASK_MAX_RETRIES: int = 3

    NOTIFICATION_CHECK_INTERVAL_SECONDS: int = 300  # 5 minutes
    STATUS_UPDATE_INTERVAL_SECONDS: int = 60  # 1 minute

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


_config = None


def get_config() -> SchedulerConfig:
    """Get singleton configuration instance."""
    global _config
    if _config is None:
        _config = SchedulerConfig()
    return _config
