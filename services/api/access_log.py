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


"""
Access-log redaction for the API service.

uvicorn's access log records each request's full path and query string. Some routes
carry secrets there (the OAuth callback's ``code`` and ``state``, the calendar
subscription token), which must not be shipped to the log backend.
"""

import logging
import re

_REDACTED = "[redacted]"
_CALENDAR_TOKEN = re.compile(r"(/api/v1/public/calendar/)[^/?\s]+")

# uvicorn.access formats '%s - "%s %s HTTP/%s" %d' with the request path as the
# third argument.
_PATH_ARG_INDEX = 2


def _redact_path(path: str) -> str:
    """Replace the calendar token and any query string in a request path."""
    redacted = _CALENDAR_TOKEN.sub(rf"\1{_REDACTED}", path)
    base, separator, _query = redacted.partition("?")
    return f"{base}?{_REDACTED}" if separator else base


class AccessLogRedactionFilter(logging.Filter):
    """Redact secrets from the request path in uvicorn access log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact the request path in place and always keep the record."""
        args = record.args
        if not isinstance(args, tuple) or len(args) <= _PATH_ARG_INDEX:
            return True
        path = args[_PATH_ARG_INDEX]
        if isinstance(path, str):
            record.args = (
                *args[:_PATH_ARG_INDEX],
                _redact_path(path),
                *args[_PATH_ARG_INDEX + 1 :],
            )
        return True
