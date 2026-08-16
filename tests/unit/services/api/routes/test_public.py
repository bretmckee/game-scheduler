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

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from services.api.routes.export import generate_calendar_filename
from services.api.routes.public import (
    calendar_router,
    get_calendar_export,
    get_image,
    head_image,
    router,
)
from shared.database import get_db
from shared.models.game import GameSession
from shared.models.game_image import GameImage


@asynccontextmanager
async def _bypass_session_cm(session):
    """Async context manager stand-in for `get_bypass_db_session()`."""
    yield session


@pytest.fixture
def mock_request():
    """Create a mock Request object."""
    request = MagicMock(spec=Request)
    request.app.state.limiter = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_image():
    """Create a sample GameImage."""
    image = GameImage()
    image.id = uuid.uuid4()
    image.image_data = b"fake image data"
    image.mime_type = "image/png"
    image.content_hash = "abc123"
    image.reference_count = 1
    return image


@pytest.mark.asyncio
async def test_get_image_success(mock_request, mock_db, sample_image):
    """Test successful image retrieval."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_image
    mock_db.execute.return_value = mock_result

    response = await get_image(mock_request, str(sample_image.id), mock_db)

    assert response.status_code == 200
    assert response.body == b"fake image data"
    assert response.media_type == "image/png"
    assert response.headers["Cache-Control"] == "public, max-age=3600"
    assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_get_image_not_found(mock_request, mock_db):
    """Test image not found returns 404."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    image_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        await get_image(mock_request, str(image_id), mock_db)

    assert exc_info.value.status_code == HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_image_database_error(mock_request, mock_db):
    """Test database error is propagated."""
    mock_db.execute.side_effect = Exception("Database connection failed")

    image_id = uuid.uuid4()
    with pytest.raises(Exception, match="Database connection failed"):
        await get_image(mock_request, str(image_id), mock_db)


@pytest.mark.asyncio
async def test_head_image_success(mock_request, mock_db, sample_image):
    """Test successful HEAD request for image metadata."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_image
    mock_db.execute.return_value = mock_result

    response = await head_image(mock_request, str(sample_image.id), mock_db)

    assert response.status_code == 200
    assert response.body == b""
    assert response.media_type == "image/png"
    assert response.headers["Cache-Control"] == "public, max-age=3600"
    assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_head_image_not_found(mock_request, mock_db):
    """Test HEAD request for non-existent image returns 404."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    image_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        await head_image(mock_request, str(image_id), mock_db)

    assert exc_info.value.status_code == HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_head_image_database_error(mock_request, mock_db):
    """Test HEAD request database error is propagated."""
    mock_db.execute.side_effect = Exception("Database connection failed")

    image_id = uuid.uuid4()
    with pytest.raises(Exception, match="Database connection failed"):
        await head_image(mock_request, str(image_id), mock_db)


@pytest.fixture
def public_app(sample_image):
    """FastAPI test app with public router and mocked database."""
    app = FastAPI()
    app.include_router(router)

    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_image
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    return app


def test_get_image_with_gif_extension_returns_200(public_app, sample_image):
    """Regression: GET with .gif extension returns 200."""
    client = TestClient(public_app)
    response = client.get(f"/api/v1/public/images/{sample_image.id}.gif")
    assert response.status_code == 200


def test_head_image_with_gif_extension_returns_200(public_app, sample_image):
    """Regression: HEAD with .gif extension returns 200."""
    client = TestClient(public_app)
    response = client.head(f"/api/v1/public/images/{sample_image.id}.gif")
    assert response.status_code == 200


def test_get_image_with_invalid_uuid_returns_404(public_app):
    """GET with non-UUID path segment returns 404."""
    client = TestClient(public_app)
    response = client.get("/api/v1/public/images/not-a-uuid.gif")
    assert response.status_code == 404


def test_head_image_with_invalid_uuid_returns_404(public_app):
    """HEAD with non-UUID path segment returns 404."""
    client = TestClient(public_app)
    response = client.head("/api/v1/public/images/not-a-uuid.gif")
    assert response.status_code == 404


@pytest.fixture
def sample_game():
    """Create a sample GameSession for calendar-export tests."""
    return GameSession(
        id="game-123",
        title="Test Game",
        host_id="user-123",
        guild_id="guild-123",
        channel_id="channel-123",
        scheduled_at=datetime(2025, 12, 15, 18, 0, 0, tzinfo=UTC),
        max_players=5,
        status="SCHEDULED",
    )


@pytest.fixture
def calendar_app():
    """FastAPI test app with calendar_router (no database dependency override)."""
    app = FastAPI()
    app.include_router(calendar_router)
    return app


@pytest.mark.asyncio
async def test_get_calendar_export_success(mock_request, mock_db, sample_game):
    """Test successful calendar export retrieval by token, with .ics extension."""
    mock_ical = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_game
    mock_db.execute.return_value = mock_result

    with (
        patch(
            "services.api.auth.tokens.get_calendar_export_token",
            new_callable=AsyncMock,
            return_value=sample_game.id,
        ),
        patch(
            "services.api.routes.public.get_bypass_db_session",
            return_value=_bypass_session_cm(mock_db),
        ),
        patch(
            "services.api.services.calendar_export.CalendarExportService.export_game",
            new_callable=AsyncMock,
            return_value=mock_ical,
        ),
    ):
        response = await get_calendar_export(mock_request, "tok123.ics")

    expected_filename = generate_calendar_filename(sample_game.title, sample_game.scheduled_at)
    assert response.status_code == 200
    assert response.media_type == "text/calendar"
    assert response.headers["Content-Disposition"] == f'inline; filename="{expected_filename}"'
    assert response.body == mock_ical


@pytest.mark.asyncio
async def test_get_calendar_export_missing_extension_still_works(
    mock_request, mock_db, sample_game
):
    """Test calendar export retrieval works when the token has no .ics suffix."""
    mock_ical = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_game
    mock_db.execute.return_value = mock_result

    with (
        patch(
            "services.api.auth.tokens.get_calendar_export_token",
            new_callable=AsyncMock,
            return_value=sample_game.id,
        ),
        patch(
            "services.api.routes.public.get_bypass_db_session",
            return_value=_bypass_session_cm(mock_db),
        ),
        patch(
            "services.api.services.calendar_export.CalendarExportService.export_game",
            new_callable=AsyncMock,
            return_value=mock_ical,
        ),
    ):
        response = await get_calendar_export(mock_request, "tok123")

    assert response.status_code == 200
    assert response.body == mock_ical


@pytest.mark.asyncio
async def test_get_calendar_export_token_not_found_returns_404(mock_request):
    """Test unknown/expired token returns 404."""
    with patch(
        "services.api.auth.tokens.get_calendar_export_token",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_calendar_export(mock_request, "tok123.ics")

    assert exc_info.value.status_code == HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_calendar_export_game_deleted_after_mint_returns_404(
    mock_request, mock_db, sample_game
):
    """Test a token that resolves to a deleted game returns 404."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with (
        patch(
            "services.api.auth.tokens.get_calendar_export_token",
            new_callable=AsyncMock,
            return_value=sample_game.id,
        ),
        patch(
            "services.api.routes.public.get_bypass_db_session",
            return_value=_bypass_session_cm(mock_db),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_calendar_export(mock_request, "tok123.ics")

    assert exc_info.value.status_code == HTTP_404_NOT_FOUND


def test_get_calendar_export_via_test_client_returns_200(calendar_app, mock_db, sample_game):
    """Regression: the rate-limited route works end-to-end via TestClient."""
    mock_ical = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_game
    mock_db.execute.return_value = mock_result

    with (
        patch(
            "services.api.auth.tokens.get_calendar_export_token",
            new_callable=AsyncMock,
            return_value=sample_game.id,
        ),
        patch(
            "services.api.routes.public.get_bypass_db_session",
            return_value=_bypass_session_cm(mock_db),
        ),
        patch(
            "services.api.services.calendar_export.CalendarExportService.export_game",
            new_callable=AsyncMock,
            return_value=mock_ical,
        ),
    ):
        client = TestClient(calendar_app)
        response = client.get("/api/v1/public/calendar/tok123.ics")

    assert response.status_code == 200
