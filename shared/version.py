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
