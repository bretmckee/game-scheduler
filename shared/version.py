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


"""
Version information for the Game Scheduler application.

This module automatically extracts version from git using setuptools-scm
when the package is installed, or falls back to environment variables
in containerized deployments.
"""

import os
from importlib.metadata import PackageNotFoundError, version

API_VERSION = "1.0.0"


def get_git_version() -> str:
    """
    Get the git version from package metadata or environment.

    Tries in order:
    1. Installed package metadata (from setuptools-scm)
    2. GIT_VERSION environment variable
    3. Fallback to "dev-unknown"

    Returns:
        Git version string (e.g., "0.0.1.dev478+gd128f6a")
    """
    try:
        return version("Game_Scheduler")
    except PackageNotFoundError:
        pass

    env_version = os.getenv("GIT_VERSION")
    if env_version:
        return env_version

    return "dev-unknown"


def get_api_version() -> str:
    """
    Get the API version.

    Returns:
        Semantic version string for API compatibility (e.g., "1.0.0")
    """
    return API_VERSION
