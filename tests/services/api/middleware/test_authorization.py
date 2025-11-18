# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Unit tests for authorization middleware."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request, Response

from services.api.middleware import authorization


@pytest.fixture
def mock_request():
    """Create mock request."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/api/v1/games"
    request.headers = {}
    return request


@pytest.fixture
def mock_response():
    """Create mock response."""
    response = MagicMock(spec=Response)
    response.status_code = 200
    return response


@pytest.fixture
def middleware():
    """Create middleware instance."""
    app = MagicMock()
    return authorization.AuthorizationMiddleware(app)


@pytest.mark.asyncio
async def test_dispatch_with_user_id(middleware, mock_request, mock_response):
    """Test dispatch with authenticated user."""
    mock_request.headers = {"X-User-Id": "user123", "X-Request-Id": "req456"}

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response == mock_response
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dispatch_without_user_id(middleware, mock_request, mock_response):
    """Test dispatch without authenticated user."""

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response == mock_response


@pytest.mark.asyncio
async def test_dispatch_403_response(middleware, mock_request):
    """Test dispatch with 403 authorization denied."""
    mock_request.headers = {"X-User-Id": "user123"}
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 403

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dispatch_401_response(middleware, mock_request):
    """Test dispatch with 401 authentication required."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 401

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_exception(middleware, mock_request):
    """Test dispatch with exception."""

    async def call_next(request):
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        await middleware.dispatch(mock_request, call_next)


@pytest.mark.asyncio
async def test_dispatch_timing(middleware, mock_request, mock_response):
    """Test dispatch measures request timing."""

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response == mock_response
