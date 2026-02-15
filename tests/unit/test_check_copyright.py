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

import importlib.util
import tempfile
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "check-copyright.py"
spec = importlib.util.spec_from_file_location("check_copyright", SCRIPT_PATH)
check_copyright = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(check_copyright)  # type: ignore[union-attr]
validate_copyright = check_copyright.validate_copyright


@pytest.fixture
def temp_files():
    """Create temporary files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        yield tmpdir_path


@pytest.fixture
def correct_copyright():
    """Return a correct copyright header."""
    return "# Copyright 2026 Bret McKee\n"


@pytest.fixture
def wrong_copyright():
    """Return an incorrect copyright header."""
    return "# Copyright 2025-2026 Wrong Author\n"


class TestCheckCopyright:
    """Test suite for check-copyright.py script."""

    def test_no_copyright_in_file(self, temp_files, correct_copyright):
        """Files without copyright should pass."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        ref_file.write_text(correct_copyright)
        source_file.write_text("print('Hello, world!')\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 0

    def test_correct_copyright_in_file(self, temp_files, correct_copyright):
        """Files with correct copyright should pass."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        ref_file.write_text(correct_copyright)
        source_file.write_text(correct_copyright + "print('Hello, world!')\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 0

    def test_wrong_copyright_in_file(self, temp_files, correct_copyright, wrong_copyright):
        """Files with wrong copyright should fail."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        ref_file.write_text(correct_copyright)
        source_file.write_text(wrong_copyright + "print('Hello, world!')\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 1

    def test_correct_copyright_partial_match(self, temp_files, correct_copyright):
        """Files with copyright that contains the reference should pass."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        full_copyright = correct_copyright + "#\n# Permission is hereby granted...\n"

        ref_file.write_text(correct_copyright)
        source_file.write_text(full_copyright + "print('Hello, world!')\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 0

    def test_empty_source_file(self, temp_files, correct_copyright):
        """Empty source files should pass (no copyright)."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        ref_file.write_text(correct_copyright)
        source_file.write_text("")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 0

    def test_missing_reference_file(self, temp_files):
        """Missing reference file should exit with code 2."""
        ref_file = temp_files / "nonexistent.py"
        source_file = temp_files / "source.py"

        source_file.write_text("print('Hello')\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 2

    def test_missing_source_file(self, temp_files, correct_copyright):
        """Missing source file should exit with code 2."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "nonexistent.py"

        ref_file.write_text(correct_copyright)

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 2

    def test_lowercase_copyright_not_detected(self, temp_files, correct_copyright):
        """Files with lowercase 'copyright' should pass (not detected)."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        ref_file.write_text(correct_copyright)
        source_file.write_text("# copyright 2025 Someone\nprint('Hello')\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 0

    def test_trailing_whitespace_in_reference(self, temp_files, correct_copyright):
        """Reference with trailing newlines should still match correctly."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        ref_file.write_text(correct_copyright + "\n\n\n")
        source_file.write_text(correct_copyright + "print('Hello')\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 0

    def test_copyright_not_at_beginning(self, temp_files, correct_copyright):
        """Copyright appearing later in file should still be detected."""
        ref_file = temp_files / "reference.py"
        source_file = temp_files / "source.py"

        ref_file.write_text(correct_copyright)
        source_file.write_text("#!/usr/bin/env python3\n" + correct_copyright + "import sys\n")

        result_code = validate_copyright(ref_file, source_file)

        assert result_code == 0
