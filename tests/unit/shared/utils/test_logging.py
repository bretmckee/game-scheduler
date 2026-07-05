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


"""Tests for shared logging utilities."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from shared.utils.logging import suppress_noisy_loggers


def _mock_loggers(names: list[str]) -> dict[str, MagicMock]:
    return {name: MagicMock() for name in names}


_LIBRARY_NAMES = ["urllib3"]


@pytest.fixture
def mock_loggers() -> dict[str, MagicMock]:
    return _mock_loggers(_LIBRARY_NAMES)


@pytest.fixture
def patched_get_logger(mock_loggers):
    real_get_logger = logging.getLogger

    def _get(name=None):
        if name in mock_loggers:
            return mock_loggers[name]
        return real_get_logger(name)

    with patch("shared.utils.logging.logging.getLogger", side_effect=_get):
        yield mock_loggers


class TestSuppressNoisyLoggers:
    def test_debug_level_uses_info_floor_for_urllib3(self, patched_get_logger):
        """At DEBUG, urllib3 is clamped to its INFO floor."""
        suppress_noisy_loggers(logging.DEBUG)

        patched_get_logger["urllib3"].setLevel.assert_called_once_with(logging.INFO)

    def test_error_level_overrides_all_floors(self, patched_get_logger):
        """At ERROR (above all floors), every library is set to ERROR."""
        suppress_noisy_loggers(logging.ERROR)

        for name in _LIBRARY_NAMES:
            patched_get_logger[name].setLevel.assert_called_once_with(logging.ERROR)

    def test_warning_level_clamps_info_floor_libraries_to_warning(self, patched_get_logger):
        """At WARNING, INFO-floor libraries are raised to WARNING."""
        suppress_noisy_loggers(logging.WARNING)

        patched_get_logger["urllib3"].setLevel.assert_called_once_with(logging.WARNING)
