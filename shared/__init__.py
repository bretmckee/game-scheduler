"""Shared package for game scheduler microservices."""

__version__ = "0.1.0"

# Export commonly used items for convenience
from shared.models import (
    Base,
    ChannelConfiguration,
    GameParticipant,
    GameSession,
    GuildConfiguration,
    User,
)
from shared.schemas import (
    GameCreateRequest,
    GameResponse,
    GuildConfigResponse,
    ParticipantResponse,
    UserResponse,
)
from shared.utils import (
    format_discord_timestamp,
    format_user_mention,
    to_unix_timestamp,
    utcnow,
)

__all__ = [
    "__version__",
    # Models
    "Base",
    "User",
    "GuildConfiguration",
    "ChannelConfiguration",
    "GameSession",
    "GameParticipant",
    # Schemas
    "UserResponse",
    "GuildConfigResponse",
    "GameCreateRequest",
    "GameResponse",
    "ParticipantResponse",
    # Utilities
    "utcnow",
    "to_unix_timestamp",
    "format_discord_timestamp",
    "format_user_mention",
]
