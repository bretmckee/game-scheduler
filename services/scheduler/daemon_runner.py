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


"""Shared signal handling and lifecycle runner for scheduler daemons."""

import logging
import signal
from collections.abc import Callable
from types import FrameType

import coverage as _coverage
from shared.telemetry import flush_telemetry

from .generic_scheduler_daemon import SchedulerDaemon

logger = logging.getLogger(__name__)


def register_shutdown_signals() -> Callable[[], bool]:
    """
    Register SIGTERM/SIGINT handlers and return a shutdown-flag callable.

    Returns a zero-argument callable that returns True once a signal has been
    received, and False before then.
    """
    flag: list[bool] = [False]

    def _signal_handler(_signum: int, _frame: FrameType | None) -> None:
        logger.info("Received signal %s, initiating graceful shutdown", _signum)
        flag[0] = True
        # Flush coverage immediately — atexit may not run if Docker escalates to SIGKILL
        cov = _coverage.Coverage.current()
        if cov is not None:
            cov.stop()
            cov.save()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    return lambda: flag[0]


def run_daemon(daemon: SchedulerDaemon) -> None:
    """
    Run a SchedulerDaemon with standard SIGTERM/SIGINT handling and telemetry flush.

    Registers signal handlers, starts the daemon loop, and ensures telemetry is
    flushed on exit regardless of how the process terminates.
    """
    shutdown_flag = register_shutdown_signals()
    try:
        daemon.run(shutdown_flag)
    finally:
        flush_telemetry()
