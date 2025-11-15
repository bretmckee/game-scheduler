"""Pydantic schemas for request/response validation."""

from shared.schemas.auth import (
    LoginRequest,
    LoginResponse,
    OAuthCallbackRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserInfoResponse,
)
from shared.schemas.channel import (
    ChannelConfigCreateRequest,
    ChannelConfigResponse,
    ChannelConfigUpdateRequest,
)
from shared.schemas.game import (
    GameCreateRequest,
    GameListResponse,
    GameResponse,
    GameUpdateRequest,
)
from shared.schemas.guild import (
    GuildConfigCreateRequest,
    GuildConfigResponse,
    GuildConfigUpdateRequest,
    GuildListResponse,
)
from shared.schemas.participant import (
    ParticipantJoinRequest,
    ParticipantResponse,
)
from shared.schemas.user import UserPreferencesRequest, UserResponse

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "OAuthCallbackRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserInfoResponse",
    # Channel
    "ChannelConfigCreateRequest",
    "ChannelConfigUpdateRequest",
    "ChannelConfigResponse",
    # Game
    "GameCreateRequest",
    "GameUpdateRequest",
    "GameResponse",
    "GameListResponse",
    # Guild
    "GuildConfigCreateRequest",
    "GuildConfigUpdateRequest",
    "GuildConfigResponse",
    "GuildListResponse",
    # Participant
    "ParticipantJoinRequest",
    "ParticipantResponse",
    # User
    "UserResponse",
    "UserPreferencesRequest",
]
