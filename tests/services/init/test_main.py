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


"""Unit tests for init service main module helpers."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from services.init.main import (
    SECONDS_PER_DAY,
    _complete_initialization,
    _initialize_telemetry_and_logging,
    _log_phase,
)


class TestInitializeTelemetryAndLogging:
    """Tests for _initialize_telemetry_and_logging helper."""

    @patch("services.init.main.init_telemetry")
    @patch("services.init.main.trace.get_tracer")
    @patch("services.init.main.datetime")
    @patch("services.init.main.logger")
    def test_initializes_telemetry_and_returns_tracer_and_time(
        self, mock_logger, mock_datetime, mock_get_tracer, mock_init_telemetry
    ):
        """Should initialize telemetry and return tracer with start time."""
        mock_tracer = Mock()
        mock_get_tracer.return_value = mock_tracer
        mock_start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_start_time

        tracer, start_time = _initialize_telemetry_and_logging()

        mock_init_telemetry.assert_called_once_with("init-service")
        mock_get_tracer.assert_called_once_with("services.init.main")
        mock_datetime.now.assert_called_once_with(UTC)
        assert tracer == mock_tracer
        assert start_time == mock_start_time
        assert mock_logger.info.call_count == 4

    @patch("services.init.main.init_telemetry")
    @patch("services.init.main.trace.get_tracer")
    @patch("services.init.main.datetime")
    @patch("services.init.main.logger")
    def test_logs_startup_banner_with_timestamp(
        self, mock_logger, mock_datetime, mock_get_tracer, mock_init_telemetry
    ):
        """Should log formatted startup banner with timestamp."""
        mock_start_time = datetime(2026, 1, 17, 15, 30, 45, tzinfo=UTC)
        mock_datetime.now.return_value = mock_start_time

        _initialize_telemetry_and_logging()

        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "=" * 60 in log_calls
        assert "Environment Initialization Started" in log_calls
        assert "Timestamp: 2026-01-17 15:30:45 UTC" in log_calls


class TestLogPhase:
    """Tests for _log_phase helper."""

    @patch("services.init.main.logger")
    def test_logs_phase_without_completion_status(self, mock_logger):
        """Should log phase message without completion checkmark."""
        _log_phase(1, 6, "Waiting for PostgreSQL...")

        mock_logger.info.assert_called_once_with("[1/6] Waiting for PostgreSQL...")

    @patch("services.init.main.logger")
    def test_logs_phase_with_completion_status(self, mock_logger):
        """Should log phase message with completion checkmark."""
        _log_phase(3, 6, "Migrations complete", completed=True)

        mock_logger.info.assert_called_once_with("✓[3/6] Migrations complete")

    @patch("services.init.main.logger")
    def test_logs_all_phases_sequentially(self, mock_logger):
        """Should log multiple phases in sequence."""
        _log_phase(1, 6, "Step 1...")
        _log_phase(1, 6, "Step 1 done", completed=True)
        _log_phase(2, 6, "Step 2...")
        _log_phase(2, 6, "Step 2 done", completed=True)

        assert mock_logger.info.call_count == 4


class TestCompleteInitialization:
    """Tests for _complete_initialization helper."""

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_logs_completion_banner_with_duration(
        self, mock_datetime, mock_path, mock_logger, mock_time
    ):
        """Should log completion banner with calculated duration."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        end_time = datetime(2026, 1, 17, 12, 5, 30, tzinfo=UTC)
        mock_datetime.now.return_value = end_time

        mock_marker = Mock()
        mock_path.return_value = mock_marker
        mock_time.sleep.side_effect = KeyboardInterrupt  # Prevent infinite loop

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        mock_datetime.now.assert_called_once_with(UTC)
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "Environment Initialization Complete" in log_calls
        assert "Duration: 330.00 seconds" in log_calls

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_creates_completion_marker_file(self, mock_datetime, mock_path, mock_logger, mock_time):
        """Should create /tmp/init-complete marker file."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = datetime(2026, 1, 17, 12, 0, 10, tzinfo=UTC)

        mock_marker = Mock()
        mock_path.return_value = mock_marker
        mock_time.sleep.side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        mock_path.assert_called_once_with("/tmp/init-complete")
        mock_marker.touch.assert_called_once()

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_enters_infinite_sleep_loop(self, mock_datetime, mock_path, mock_logger, mock_time):
        """Should enter infinite sleep loop with SECONDS_PER_DAY interval."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = datetime(2026, 1, 17, 12, 0, 5, tzinfo=UTC)

        mock_time.sleep.side_effect = [None, None, KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        assert mock_time.sleep.call_count == 3
        mock_time.sleep.assert_called_with(SECONDS_PER_DAY)

    @patch("services.init.main.time")
    @patch("services.init.main.logger")
    @patch("services.init.main.Path")
    @patch("services.init.main.datetime")
    def test_logs_sleep_mode_message(self, mock_datetime, mock_path, mock_logger, mock_time):
        """Should log message about entering sleep mode."""

        start_time = datetime(2026, 1, 17, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = datetime(2026, 1, 17, 12, 0, 5, tzinfo=UTC)

        mock_time.sleep.side_effect = KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            _complete_initialization(start_time)

        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "Entering sleep mode. Container will remain healthy." in log_calls
