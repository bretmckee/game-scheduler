#!/usr/bin/env python3
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

import sys
from pathlib import Path

EXPECTED_ARG_COUNT = 3


def validate_copyright(copyright_file: Path, source_file: Path) -> int:
    """
    Validate copyright header in a source file.

    Compares a copyright reference file against a source file. Returns 0 if:
    - Source file contains no "Copyright" keyword, OR
    - Source file contains the expected copyright as a substring

    Returns 1 if source file has a copyright that doesn't match expected.
    Returns 2 if file reading fails.

    Args:
        copyright_file: Path to the reference copyright file
        source_file: Path to the source file to validate

    Returns:
        Exit code: 0 for success, 1 for wrong copyright, 2 for errors
    """
    try:
        expected = copyright_file.read_text(encoding="utf-8").strip()
        content = source_file.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e.filename}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"ERROR: Failed to read file: {e}", file=sys.stderr)
        return 2

    if "Copyright" not in content or expected in content:
        return 0

    print(f"ERROR: Wrong copyright in {source_file}")
    print("Remove the manual copyright - autocopyright will add the correct one")
    return 1


def main() -> int:
    """Command-line interface for copyright validation."""
    if len(sys.argv) != EXPECTED_ARG_COUNT:
        print(f"Usage: {sys.argv[0]} <copyright_file> <source_file>", file=sys.stderr)
        return 2

    copyright_file = Path(sys.argv[1])
    source_file = Path(sys.argv[2])

    return validate_copyright(copyright_file, source_file)


if __name__ == "__main__":
    sys.exit(main())
