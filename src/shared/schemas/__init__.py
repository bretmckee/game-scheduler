"""
Pydantic schemas for request/response validation and serialization.
"""

from .auth import GuildInfo, LoginResponse, UserInfo
from .game import (
    CreateGameRequest,
    GameDetailsResponse,
    GameResponse,
    JoinGameResponse,
    UpdateGameRequest,
)
from .guild_config import (
    ChannelConfigRequest,
    ChannelConfigResponse,
    GuildConfigRequest,
    GuildConfigResponse,
)
from .participant import ParticipantResponse, ParticipantValidationError

__all__ = [
    # Auth schemas
    "LoginResponse",
    "UserInfo",
    "GuildInfo",
    # Game schemas
    "CreateGameRequest",
    "GameResponse",
    "GameDetailsResponse",
    "UpdateGameRequest",
    "JoinGameResponse",
    # Configuration schemas
    "GuildConfigRequest",
    "GuildConfigResponse",
    "ChannelConfigRequest",
    "ChannelConfigResponse",
    # Participant schemas
    "ParticipantResponse",
    "ParticipantValidationError",
]
