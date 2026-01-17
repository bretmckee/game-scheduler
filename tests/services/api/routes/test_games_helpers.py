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


"""
Unit tests for games route helper functions.

Tests the extracted helper functions from update_game refactoring.
"""

import json
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from services.api.routes.games import _parse_update_form_data, _process_image_upload


class TestParseUpdateFormData:
    """Tests for _parse_update_form_data helper function."""

    def test_parse_all_fields_provided(self):
        """Parse all fields when provided."""
        scheduled_at = "2026-01-20T18:00:00Z"
        reminder_minutes = json.dumps([60, 15])
        notify_role_ids = json.dumps(["role1", "role2"])
        participants = json.dumps([{"type": "discord", "id": "user1"}])
        removed_participant_ids = json.dumps(["part1", "part2"])

        (
            scheduled_at_dt,
            reminder_list,
            role_ids_list,
            participants_list,
            removed_list,
        ) = _parse_update_form_data(
            scheduled_at, reminder_minutes, notify_role_ids, participants, removed_participant_ids
        )

        assert scheduled_at_dt == datetime(2026, 1, 20, 18, 0, 0, tzinfo=UTC)
        assert reminder_list == [60, 15]
        assert role_ids_list == ["role1", "role2"]
        assert participants_list == [{"type": "discord", "id": "user1"}]
        assert removed_list == ["part1", "part2"]

    def test_parse_all_fields_none(self):
        """Parse returns None for all fields when None provided."""
        (
            scheduled_at_dt,
            reminder_list,
            role_ids_list,
            participants_list,
            removed_list,
        ) = _parse_update_form_data(None, None, None, None, None)

        assert scheduled_at_dt is None
        assert reminder_list is None
        assert role_ids_list is None
        assert participants_list is None
        assert removed_list is None

    def test_parse_scheduled_at_with_z_suffix(self):
        """Parse ISO datetime with Z suffix correctly."""
        scheduled_at = "2026-02-14T12:30:00Z"

        (scheduled_at_dt, _, _, _, _) = _parse_update_form_data(
            scheduled_at, None, None, None, None
        )

        assert scheduled_at_dt == datetime(2026, 2, 14, 12, 30, 0, tzinfo=UTC)

    def test_parse_scheduled_at_with_timezone_offset(self):
        """Parse ISO datetime with timezone offset."""
        scheduled_at = "2026-02-14T12:30:00+05:00"

        (scheduled_at_dt, _, _, _, _) = _parse_update_form_data(
            scheduled_at, None, None, None, None
        )

        # Should parse the timezone offset correctly
        assert scheduled_at_dt.hour == 12
        assert scheduled_at_dt.tzinfo is not None

    def test_parse_empty_json_arrays(self):
        """Parse empty JSON arrays correctly."""
        (
            _,
            reminder_list,
            role_ids_list,
            participants_list,
            removed_list,
        ) = _parse_update_form_data(None, "[]", "[]", "[]", "[]")

        assert reminder_list == []
        assert role_ids_list == []
        assert participants_list == []
        assert removed_list == []

    def test_parse_complex_participants(self):
        """Parse complex participant JSON structures."""
        participants = json.dumps([
            {"type": "discord", "id": "123456"},
            {"type": "placeholder", "display_name": "Guest Player"},
        ])

        (_, _, _, participants_list, _) = _parse_update_form_data(
            None, None, None, participants, None
        )

        assert len(participants_list) == 2
        assert participants_list[0]["type"] == "discord"
        assert participants_list[1]["display_name"] == "Guest Player"


class TestProcessImageUpload:
    """Tests for _process_image_upload helper function."""

    async def test_process_remove_flag_returns_empty_bytes(self):
        """Returns empty bytes and empty string when remove flag is True."""
        image_data, mime_type = await _process_image_upload(None, True, "thumbnail", "game123")

        assert image_data == b""
        assert mime_type == ""

    async def test_process_no_file_returns_none(self):
        """Returns None tuple when no file and remove flag False."""
        image_data, mime_type = await _process_image_upload(None, False, "thumbnail", "game123")

        assert image_data is None
        assert mime_type is None

    async def test_process_valid_image_upload(self):
        """Process valid image upload successfully."""
        # Create mock UploadFile
        file_content = b"fake image data"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.png"
        mock_file.content_type = "image/png"
        mock_file.size = len(file_content)
        mock_file.file = BytesIO(file_content)
        mock_file.read = AsyncMock(return_value=file_content)

        # Mock the file operations
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=len(file_content))

        image_data, mime_type = await _process_image_upload(
            mock_file, False, "thumbnail", "game123"
        )

        assert image_data == file_content
        assert mime_type == "image/png"
        mock_file.read.assert_called_once()

    async def test_process_different_image_types(self):
        """Process different image MIME types correctly."""
        for content_type in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
            file_content = b"image data"
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.jpg"
            mock_file.content_type = content_type
            mock_file.size = len(file_content)
            mock_file.file = BytesIO(file_content)
            mock_file.read = AsyncMock(return_value=file_content)
            mock_file.file.seek = MagicMock()
            mock_file.file.tell = MagicMock(return_value=len(file_content))

            _, mime_type = await _process_image_upload(mock_file, False, "image", "game123")

            assert mime_type == content_type

    async def test_process_remove_flag_takes_precedence_over_file(self):
        """Remove flag takes precedence even when file provided."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock()

        image_data, mime_type = await _process_image_upload(mock_file, True, "thumbnail", "game123")

        assert image_data == b""
        assert mime_type == ""
        mock_file.read.assert_not_called()

    async def test_process_invalid_file_type_raises_exception(self):
        """Invalid file type raises HTTPException."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = 100
        mock_file.file = BytesIO(b"text content")
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=100)

        with pytest.raises(HTTPException) as exc_info:
            await _process_image_upload(mock_file, False, "thumbnail", "game123")

        assert exc_info.value.status_code == 400
        assert "PNG, JPEG, GIF, or WebP" in exc_info.value.detail

    async def test_process_file_too_large_raises_exception(self):
        """File larger than 5MB raises HTTPException."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.png"
        mock_file.content_type = "image/png"
        mock_file.size = 6 * 1024 * 1024  # 6MB
        mock_file.file = BytesIO(b"x" * (6 * 1024 * 1024))
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=6 * 1024 * 1024)

        with pytest.raises(HTTPException) as exc_info:
            await _process_image_upload(mock_file, False, "image", "game123")

        assert exc_info.value.status_code == 400
        assert "less than 5MB" in exc_info.value.detail
