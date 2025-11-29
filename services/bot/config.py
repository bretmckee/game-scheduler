"""Bot configuration management."""

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class BotConfig(BaseSettings):
    """
    Discord bot configuration loaded from environment variables.

    Attributes:
        discord_bot_token: Discord bot authentication token
        discord_client_id: Discord application ID for OAuth2
        database_url: PostgreSQL connection string with asyncpg driver
        rabbitmq_url: RabbitMQ AMQP connection string
        redis_url: Redis connection string
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment name (development, staging, production)
    """

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Make Discord tokens optional for integration tests
    discord_bot_token: str | None = Field(default=None, description="Discord bot token")
    discord_client_id: str | None = Field(default=None, description="Discord application ID")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/game_scheduler",
        description="PostgreSQL connection URL",
    )

    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    environment: str = Field(
        default="development",
        description="Environment name",
    )


_config: BotConfig | None = None


def get_config() -> BotConfig:
    """
    Get or create global bot configuration instance.

    Returns:
        Singleton BotConfig instance loaded from environment variables
    """
    global _config
    if _config is None:
        _config = BotConfig()
    return _config
