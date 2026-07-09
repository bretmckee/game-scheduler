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
"""Check diff coverage for changed Python files."""

import os
import re
import shutil
import subprocess  # noqa: S404
import sys

_PY_SOURCE_PATTERN = re.compile(r"^(services|shared)/.*\.py$")


def main() -> int:
    """Run diff coverage check on changed Python source files."""
    git_path = shutil.which("git")
    if not git_path:
        print("git command not found in PATH")
        return 1

    base_ref = os.environ.get("BASE_REF")
    git_cmd = (
        [git_path, "diff", f"{base_ref}..HEAD", "--name-only", "--diff-filter=ACM"]
        if base_ref
        else [git_path, "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    )

    result = subprocess.run(  # noqa: S603
        git_cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print("Failed to get changed files")
        return 1

    changed_files = result.stdout.strip().split()
    py_files = [f for f in changed_files if _PY_SOURCE_PATTERN.match(f) and "__pycache__" not in f]

    if not py_files:
        return 0

    branch = base_ref if base_ref else "origin/main"
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "diff_cover.diff_cover_tool",
            "coverage.xml",
            f"--compare-branch={branch}",
            "--fail-under=90",
            "--ignore-whitespace",
            "--quiet",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Diff coverage check failed for {len(py_files)} Python files...")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
