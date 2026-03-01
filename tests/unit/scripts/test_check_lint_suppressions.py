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


"""Unit tests for scripts/check_lint_suppressions.py."""

import importlib.util
import io
import os
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

_SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "scripts" / "check_lint_suppressions.py"
_spec = importlib.util.spec_from_file_location("check_lint_suppressions", _SCRIPT_PATH)
_mod: ModuleType = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

check_lint_suppressions = _mod


def _make_added_diff(filename: str, *added_lines: str, start_line: int = 1) -> str:
    """Build a minimal staged diff with only added lines."""
    count = len(added_lines)
    hunk = f"@@ -0,0 +{start_line},{count} @@"
    body = "\n".join(f"+{line}" for line in added_lines)
    return f"+++ b/{filename}\n{hunk}\n{body}\n"


def _run_main(diff: str, approved_overrides: str | None = None) -> tuple[int, str]:
    """Run main() with a mocked diff and return (exit_code, stdout)."""
    mock_result = mock.Mock(stdout=diff)

    if approved_overrides is not None:
        env_patch = {"APPROVED_OVERRIDES": approved_overrides}
        clear = False
    else:
        env_patch = {k: v for k, v in os.environ.items() if k != "APPROVED_OVERRIDES"}
        clear = True

    stdout_buf = io.StringIO()
    with mock.patch.object(check_lint_suppressions.subprocess, "run", return_value=mock_result):
        with mock.patch.dict(os.environ, env_patch, clear=clear):
            with mock.patch("sys.stdout", stdout_buf):
                try:
                    check_lint_suppressions.main()
                    return 0, stdout_buf.getvalue()
                except SystemExit as exc:
                    code = exc.code if isinstance(exc.code, int) else 1
                    return code, stdout_buf.getvalue()


def test_clean_diff_exits_zero():
    diff = _make_added_diff("clean.py", "x = 1")
    code, _ = _run_main(diff)
    assert code == 0


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa", "bare noqa"),
        ("# ruff: noqa", "ruff file noqa"),
        ("x: int = value  # type: ignore", "bare type ignore"),
        ("#lizard forgive global", "lizard forgive global"),
        ("// @ts-ignore", "ts-ignore"),
        ("// eslint-disable", "eslint-disable bare"),
        ("/* eslint-disable */", "eslint-disable block"),
    ],
)
def test_blocked_pattern_exits_nonzero(line, label):
    diff = _make_added_diff("file.py", line)
    code, out = _run_main(diff)
    assert code != 0, f"Expected nonzero exit for {label}"
    assert "file.py:1:" in out, f"Expected file:line in output for {label}"


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa", "bare noqa"),
        ("# ruff: noqa", "ruff file noqa"),
        ("x: int = value  # type: ignore", "bare type ignore"),
        ("#lizard forgive global", "lizard forgive global"),
        ("// @ts-ignore", "ts-ignore"),
        ("// eslint-disable", "eslint-disable bare"),
        ("/* eslint-disable */", "eslint-disable block"),
    ],
)
def test_blocked_pattern_output_references_instructions(line, label):
    diff = _make_added_diff("file.py", line)
    _, out = _run_main(diff)
    instructions = "quality-check-overrides.instructions.md"
    assert instructions in out, f"Expected instructions ref for {label}"


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa: E501", "specific noqa code"),
        ("x = y  # type: ignore[attr-defined]", "specific type ignore"),
        ("#lizard forgives", "lizard forgives bare"),
        ("// @ts-expect-error", "ts-expect-error"),
        ("// eslint-disable-next-line no-console", "eslint-disable-next-line specific"),
    ],
)
def test_counted_pattern_fails_without_approval(line, label):
    diff = _make_added_diff("file.py", line)
    code, out = _run_main(diff, approved_overrides=None)
    assert code != 0, f"Expected nonzero exit for {label} with no approval"
    assert "quality-check-overrides.instructions.md" in out


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa: E501", "specific noqa code"),
        ("x = y  # type: ignore[attr-defined]", "specific type ignore"),
        ("#lizard forgives", "lizard forgives bare"),
        ("// @ts-expect-error", "ts-expect-error"),
        ("// eslint-disable-next-line no-console", "eslint-disable-next-line specific"),
    ],
)
def test_counted_pattern_passes_with_approval(line, label):
    diff = _make_added_diff("file.py", line)
    code, _ = _run_main(diff, approved_overrides="1")
    assert code == 0, f"Expected zero exit for {label} with APPROVED_OVERRIDES=1"


def test_approved_overrides_1_does_not_permit_bare_noqa():
    diff = _make_added_diff("file.py", "x = 1  # noqa")
    code, out = _run_main(diff, approved_overrides="1")
    assert code != 0
    assert "file.py:1:" in out


def test_removal_lines_are_not_scanned():
    diff = "+++ b/file.py\n@@ -1,1 +0,0 @@\n-x = 1  # noqa\n"
    code, _ = _run_main(diff)
    assert code == 0


def test_plus_plus_plus_header_not_scanned():
    diff = "+++ b/file.py\n@@ -0,0 +1,1 @@\n+x = 1\n"
    code, _ = _run_main(diff)
    assert code == 0


def test_mixed_bare_and_counted_fails_on_bare():
    diff = _make_added_diff(
        "file.py",
        "x = 1  # noqa",
        "y = 2  # noqa: E501",
    )
    code, out = _run_main(diff, approved_overrides="1")
    assert code != 0
    assert "file.py:1:" in out


# ---------------------------------------------------------------------------
# Task 1.4 edge case tests (REFACTOR phase — no xfail)
# ---------------------------------------------------------------------------


def test_approved_overrides_2_allows_two_counted():
    diff = _make_added_diff(
        "file.py",
        "x = 1  # noqa: E501",
        "y = 2  # noqa: E501",
    )
    code, _ = _run_main(diff, approved_overrides="2")
    assert code == 0


def test_approved_overrides_2_blocks_three_counted():
    diff = _make_added_diff(
        "file.py",
        "x = 1  # noqa: E501",
        "y = 2  # noqa: E501",
        "z = 3  # noqa: E501",
    )
    code, out = _run_main(diff, approved_overrides="2")
    assert code != 0
    assert "quality-check-overrides.instructions.md" in out


def test_lizard_forgives_with_metric_is_counted():
    diff = _make_added_diff("file.py", "#lizard forgives(length)")
    code, _ = _run_main(diff, approved_overrides="1")
    assert code == 0


def test_line_matching_blocked_and_counted_is_treated_as_blocked():
    # A line with both a bare noqa (blocked) and a specific noqa (counted).
    # The blocked phase runs first and exits, so the counted phase is never reached.
    diff = _make_added_diff("file.py", "x = 1  # noqa  # noqa: E501")
    code, out = _run_main(diff, approved_overrides="1")
    assert code != 0
    assert "Bare/blanket" in out
    assert "file.py:1:" in out
