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


"""Unit tests for scripts/check_commit_duplicates.py."""

import importlib.util
import inspect
import json
import tempfile
from pathlib import Path
from types import ModuleType
from unittest import mock

_SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "scripts" / "check_commit_duplicates.py"
_spec = importlib.util.spec_from_file_location("check_commit_duplicates", _SCRIPT_PATH)
_mod: ModuleType = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

check_commit_duplicates = _mod

_EMPTY_REPORT = json.dumps({"duplicates": []})


def _run_subprocess_mock(diff_output: str) -> mock.Mock:
    """Build a subprocess.run mock that returns the given diff text."""
    result = mock.Mock()
    result.stdout = diff_output
    return result


def _make_diff(filename: str, *added_lines: str, start_line: int = 1) -> str:
    """Build a minimal git diff with added lines in the given file."""
    count = len(added_lines)
    hunk = f"@@ -0,0 +{start_line},{count} @@"
    body = "\n".join(f"+{line}" for line in added_lines)
    return f"+++ b/{filename}\n{hunk}\n{body}\n"


# ---------------------------------------------------------------------------
# get_changed_line_ranges() — diff source selection
# ---------------------------------------------------------------------------


def test_get_changed_line_ranges_with_compare_branch_uses_three_dot_diff():
    """When compare_branch is given, git diff uses <branch>...HEAD, not --cached."""
    diff = _make_diff("services/api/main.py", "x = 1", "y = 2")
    mock_result = _run_subprocess_mock(diff)

    with mock.patch.object(
        check_commit_duplicates.subprocess, "run", return_value=mock_result
    ) as mock_run:
        check_commit_duplicates.get_changed_line_ranges(compare_branch="origin/main")

    args = mock_run.call_args[0][0]
    assert "origin/main...HEAD" in args
    assert "--cached" not in args
    assert "--unified=0" in args


def test_get_changed_line_ranges_without_compare_branch_uses_cached():
    """When compare_branch is absent, git diff uses --cached (pre-commit behaviour)."""
    diff = _make_diff("services/api/main.py", "x = 1")
    mock_result = _run_subprocess_mock(diff)

    with mock.patch.object(
        check_commit_duplicates.subprocess, "run", return_value=mock_result
    ) as mock_run:
        check_commit_duplicates.get_changed_line_ranges()

    args = mock_run.call_args[0][0]
    assert "--cached" in args
    assert "--unified=0" in args


# ---------------------------------------------------------------------------
# main() — compare_branch parameter passthrough
# ---------------------------------------------------------------------------


def test_main_accepts_compare_branch_parameter():
    """main() must accept compare_branch as an optional keyword argument."""
    sig = inspect.signature(check_commit_duplicates.main)
    assert "compare_branch" in sig.parameters


def test_main_passes_compare_branch_to_get_changed_line_ranges():
    """main() passes compare_branch through to get_changed_line_ranges()."""
    diff = _make_diff("services/api/main.py", "x = 1")
    mock_result = _run_subprocess_mock(diff)

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", encoding="utf-8", delete=False) as f:
        f.write(_EMPTY_REPORT)
        report_path = f.name

    with mock.patch.object(
        check_commit_duplicates.subprocess, "run", return_value=mock_result
    ) as mock_run:
        check_commit_duplicates.main(report_file=report_path, compare_branch="origin/main")

    args = mock_run.call_args[0][0]
    assert "origin/main...HEAD" in args


# ---------------------------------------------------------------------------
# Empty diff — must not raise; exit 0
# ---------------------------------------------------------------------------


def test_empty_diff_returns_empty_dict():
    """Empty git diff output produces an empty dict with no error."""
    mock_result = _run_subprocess_mock("")

    with mock.patch.object(check_commit_duplicates.subprocess, "run", return_value=mock_result):
        result = check_commit_duplicates.get_changed_line_ranges()

    assert result == {}


def test_empty_diff_with_compare_branch_returns_empty_dict():
    """Empty diff with compare_branch also returns {} without raising."""
    mock_result = _run_subprocess_mock("")

    with mock.patch.object(check_commit_duplicates.subprocess, "run", return_value=mock_result):
        result = check_commit_duplicates.get_changed_line_ranges(compare_branch="origin/main")

    assert result == {}


def test_main_with_empty_diff_exits_zero():
    """main() exits 0 when there are no changed lines (nothing to check)."""
    mock_result = _run_subprocess_mock("")

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", encoding="utf-8", delete=False) as f:
        f.write(_EMPTY_REPORT)
        report_path = f.name

    with mock.patch.object(check_commit_duplicates.subprocess, "run", return_value=mock_result):
        exit_code = check_commit_duplicates.main(report_file=report_path)

    assert exit_code == 0
