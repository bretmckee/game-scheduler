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


"""Unit tests for the retry daemon wrapper."""

import logging
from unittest.mock import MagicMock, patch

import services.retry.retry_daemon_wrapper as wrapper


class TestMainLogging:
    @patch("services.retry.retry_daemon_wrapper.flush_telemetry")
    @patch("services.retry.retry_daemon_wrapper.init_telemetry")
    @patch("services.retry.retry_daemon_wrapper.RetryDaemon")
    def test_log_level_defaults_to_info(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush, monkeypatch
    ):
        """LOG_LEVEL defaults to INFO when the env var is absent."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        with patch("services.retry.retry_daemon_wrapper.logging.basicConfig") as mock_cfg:
            wrapper.main()

        assert mock_cfg.call_args.kwargs["level"] == logging.INFO

    @patch("services.retry.retry_daemon_wrapper.flush_telemetry")
    @patch("services.retry.retry_daemon_wrapper.init_telemetry")
    @patch("services.retry.retry_daemon_wrapper.RetryDaemon")
    def test_log_level_respects_env_var(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush, monkeypatch
    ):
        """LOG_LEVEL env var is passed to basicConfig."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        with patch("services.retry.retry_daemon_wrapper.logging.basicConfig") as mock_cfg:
            wrapper.main()

        assert mock_cfg.call_args.kwargs["level"] == logging.DEBUG

    @patch("services.retry.retry_daemon_wrapper.flush_telemetry")
    @patch("services.retry.retry_daemon_wrapper.init_telemetry")
    @patch("services.retry.retry_daemon_wrapper.RetryDaemon")
    def test_calls_suppress_noisy_loggers(
        self, mock_daemon_cls, mock_init_telemetry, mock_flush, monkeypatch
    ):
        """suppress_noisy_loggers is called with the resolved log level."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda flag: None
        mock_daemon_cls.return_value = mock_instance

        with patch("services.retry.retry_daemon_wrapper.suppress_noisy_loggers") as mock_suppress:
            wrapper.main()

        mock_suppress.assert_called_once_with(logging.DEBUG)
