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
    # Models
    "Base",
    "ChannelConfiguration",
    "GameCreateRequest",
    "GameParticipant",
    "GameResponse",
    "GameSession",
    "GuildConfigResponse",
    "GuildConfiguration",
    "ParticipantResponse",
    "User",
    # Schemas
    "UserResponse",
    "__version__",
    "format_discord_timestamp",
    "format_user_mention",
    "to_unix_timestamp",
    # Utilities
    "utcnow",
]
