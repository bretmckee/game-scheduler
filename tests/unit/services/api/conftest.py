# Copyright 2026 Bret McKee
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


"""Shared fixtures for API tests (routes and services).

This conftest.py is inherited by all tests in:
- tests/unit/services/api/routes/
- tests/unit/services/api/services/
- tests/unit/services/api/dependencies/

Provides:
- Mock Redis client and member projection functions for unit tests
- Prevents real Redis connections in unit test environment
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_get_redis_client():
    """Auto-mock get_redis_client for all API tests.

    Prevents unit tests from attempting real Redis connections.
    Mocks both get_redis_client and member_projection functions
    that are commonly used in API tests.
    """
    mock_redis = AsyncMock()
    with (
        patch(
            "services.api.dependencies.permissions.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "services.api.dependencies.permissions.member_projection.is_bot_fresh",
            return_value=True,
        ),
        patch(
            "services.api.dependencies.permissions.member_projection.get_user_guilds",
            return_value=[
                "123456789012345678",
                "987654321",
                "111222333",
                "other_guild_id",
            ],
        ),
        patch(
            "services.api.dependencies.permissions.member_projection.get_guild_name",
            return_value="Test Guild",
        ),
    ):
        yield mock_redis
