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


"""Tests for version information module."""

from unittest.mock import MagicMock

import shared.version as version_module
from shared.version import API_VERSION, get_api_version, get_git_version


class TestGetGitVersion:
    """Tests for get_git_version function."""

    def test_returns_version_from_build_version_file(self, monkeypatch):
        """Should read version from .build_version file written at Docker build time."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "2.0.0.post5+g1234abc"
        monkeypatch.setattr(version_module, "_BUILD_VERSION_FILE", mock_file)

        assert get_git_version() == "2.0.0.post5+g1234abc"

    def test_returns_dev_unknown_when_file_absent(self, monkeypatch):
        """Should return 'dev-unknown' when .build_version does not exist."""
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        monkeypatch.setattr(version_module, "_BUILD_VERSION_FILE", mock_file)

        assert get_git_version() == "dev-unknown"

    def test_returns_dev_unknown_when_file_is_blank(self, monkeypatch):
        """Should return 'dev-unknown' when .build_version exists but contains only whitespace."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "   "
        monkeypatch.setattr(version_module, "_BUILD_VERSION_FILE", mock_file)

        assert get_git_version() == "dev-unknown"


class TestGetApiVersion:
    """Tests for get_api_version function."""

    def test_returns_api_version_constant(self):
        """Should return the API_VERSION constant value."""
        result = get_api_version()

        assert result == API_VERSION

    def test_api_version_is_semantic_version(self):
        """API version should follow semantic versioning format."""
        result = get_api_version()

        # Basic semantic version validation (major.minor.patch)
        parts = result.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_api_version_constant_matches_function(self):
        """The function should return exactly what the constant contains."""
        assert get_api_version() == API_VERSION
        assert API_VERSION == "1.0.0"


class TestVersionModuleIntegration:
    """Integration tests for version module behavior."""

    def test_version_functions_do_not_raise_exceptions(self):
        """Both version functions should never raise exceptions."""
        git_version = get_git_version()
        api_version = get_api_version()

        assert isinstance(git_version, str)
        assert isinstance(api_version, str)
        assert len(git_version) > 0
        assert len(api_version) > 0
