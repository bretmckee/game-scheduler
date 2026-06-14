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


"""Logging utilities shared across services."""

import logging

_NOISY_THIRD_PARTY_LOGGERS: dict[str, int] = {
    "aiormq": logging.INFO,
    "aio_pika": logging.INFO,
    "pika": logging.WARNING,
    "urllib3": logging.INFO,
}


def suppress_noisy_loggers(log_level: int) -> None:
    """Set third-party infrastructure loggers to at least their configured floor.

    Each library has a minimum log level that prevents its routine operational
    messages from drowning out application logs.  For example, pika emits ~14
    INFO-level lines per connection lifecycle (connect, channel, close), so its
    floor is WARNING.
    """
    for name, floor in _NOISY_THIRD_PARTY_LOGGERS.items():
        effective_level = max(floor, log_level)
        logging.getLogger(name).setLevel(effective_level)
