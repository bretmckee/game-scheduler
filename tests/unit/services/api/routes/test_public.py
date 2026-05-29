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
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from services.api.routes.public import get_image, head_image, router
from shared.database import get_db
from shared.models.game_image import GameImage


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
