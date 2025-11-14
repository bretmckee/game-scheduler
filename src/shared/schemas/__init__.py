"""
Pydantic schemas for request/response validation and serialization.
"""

from .auth import LoginResponse, UserInfo, GuildInfo
from .game import (
    CreateGameRequest,
    GameResponse,
    GameDetailsResponse,
    UpdateGameRequest,
    JoinGameResponse,
)
from .guild_config import (
    GuildConfigRequest,
    GuildConfigResponse,
    ChannelConfigRequest,
    ChannelConfigResponse,
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