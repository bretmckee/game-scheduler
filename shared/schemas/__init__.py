# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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
from shared.schemas.template import (
    TemplateCreateRequest,
    TemplateListItem,
    TemplateReorderRequest,
    TemplateResponse,
    TemplateUpdateRequest,
)
from shared.schemas.user import UserPreferencesRequest, UserResponse

__all__ = [
    # Channel
    "ChannelConfigCreateRequest",
    "ChannelConfigResponse",
    "ChannelConfigUpdateRequest",
    # Game
    "GameCreateRequest",
    "GameListResponse",
    "GameResponse",
    "GameUpdateRequest",
    # Guild
    "GuildConfigCreateRequest",
    "GuildConfigResponse",
    "GuildConfigUpdateRequest",
    "GuildListResponse",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "OAuthCallbackRequest",
    # Participant
    "ParticipantJoinRequest",
    "ParticipantResponse",
    "RefreshTokenRequest",
    # Template
    "TemplateCreateRequest",
    "TemplateListItem",
    "TemplateReorderRequest",
    "TemplateResponse",
    "TemplateUpdateRequest",
    "TokenResponse",
    "UserInfoResponse",
    "UserPreferencesRequest",
    # User
    "UserResponse",
]
