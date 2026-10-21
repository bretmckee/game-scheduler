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


"""Tests for access-log redaction."""

import logging

import pytest

from services.api import access_log

_UVICORN_ACCESS_FORMAT = '%s - "%s %s HTTP/%s" %d'


def _record(path: str) -> logging.LogRecord:
    """Build a record shaped like the ones uvicorn.access emits."""
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=_UVICORN_ACCESS_FORMAT,
        args=("172.18.0.9:51234", "GET", path, "1.1", 200),
        exc_info=None,
    )


@pytest.fixture
def redactor() -> access_log.AccessLogRedactionFilter:
    return access_log.AccessLogRedactionFilter()


def test_query_string_is_redacted(redactor):
    """OAuth code/state and any other query values never reach the log."""
    record = _record("/api/v1/auth/callback?code=SECRETCODE&state=SECRETSTATE")

    assert redactor.filter(record) is True

    assert record.getMessage() == (
        '172.18.0.9:51234 - "GET /api/v1/auth/callback?[redacted] HTTP/1.1" 200'
    )


def test_calendar_token_is_redacted(redactor):
    """The calendar subscription token in the path is replaced."""
    record = _record("/api/v1/public/calendar/SECRETTOKEN.ics")

    redactor.filter(record)

    assert record.getMessage() == (
        '172.18.0.9:51234 - "GET /api/v1/public/calendar/[redacted] HTTP/1.1" 200'
    )


def test_calendar_token_and_query_are_both_redacted(redactor):
    """Both secret locations are handled in one path."""
    record = _record("/api/v1/public/calendar/SECRETTOKEN.ics?download=1")

    redactor.filter(record)

    assert "SECRETTOKEN" not in record.getMessage()
    assert record.getMessage().endswith(
        '/api/v1/public/calendar/[redacted]?[redacted] HTTP/1.1" 200'
    )


def test_ordinary_path_is_unchanged_and_record_kept(redactor):
    """Paths without secrets are logged exactly as before."""
    record = _record("/api/v1/games/ac4e410f-9b4c-44e8-b000-1e0a0146cc8d")

    assert redactor.filter(record) is True

    assert record.getMessage() == (
        '172.18.0.9:51234 - "GET /api/v1/games/ac4e410f-9b4c-44e8-b000-1e0a0146cc8d HTTP/1.1" 200'
    )


def test_unexpected_record_shape_is_kept_untouched(redactor):
    """A record that does not look like an access line is passed through unchanged."""
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 0, "plain message", None, None
    )

    assert redactor.filter(record) is True

    assert record.getMessage() == "plain message"
