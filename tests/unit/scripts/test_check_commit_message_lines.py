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


"""Unit tests for scripts/check_commit_message_lines.py."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "check_commit_message_lines.py"
)
_spec = importlib.util.spec_from_file_location("check_commit_message_lines", _SCRIPT_PATH)
_mod: ModuleType = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

check_commit_message_lines = _mod


@pytest.fixture
def message_file(tmp_path: Path):
    """Write a commit message file and return its path (callable by content)."""

    def _write(content: str) -> Path:
        path = tmp_path / "COMMIT_EDITMSG"
        path.write_text(content, encoding="utf-8")
        return path

    return _write


class TestFindViolations:
    def test_short_lines_pass(self) -> None:
        lines = ["feat: add health endpoint", "", "- bullet one", "- bullet two"]
        assert check_commit_message_lines._find_violations(lines) == []

    def test_exactly_at_limit_passes(self) -> None:
        line = "x" * check_commit_message_lines.MAX_LINE_LENGTH
        assert check_commit_message_lines._find_violations([line]) == []

    def test_line_over_limit_fails(self) -> None:
        line = "Rationale: " + "detail" * 30
        violations = check_commit_message_lines._find_violations(["subject", line])
        assert len(violations) == 1
        number, text = violations[0]
        assert number == 2
        assert text == line

    def test_comment_lines_are_ignored(self) -> None:
        long_comment = "# " + "a" * 200
        short_subject = "feat: something short"
        assert check_commit_message_lines._find_violations([short_subject, long_comment]) == []

    def test_indented_comment_is_ignored(self) -> None:
        lines = ["subject", "  # indented comment " + "b" * 150]
        assert check_commit_message_lines._find_violations(lines) == []

    def test_trailing_whitespace_not_counted(self) -> None:
        line = "y" * (check_commit_message_lines.MAX_LINE_LENGTH - 5) + "      "
        assert check_commit_message_lines._find_violations([line]) == []

    def test_multiple_violations_report_line_numbers(self) -> None:
        lines = ["ok", "z" * 90, "fine", "w" * 81]
        violations = check_commit_message_lines._find_violations(lines)
        assert [number for number, _ in violations] == [2, 4]


class TestMain:
    def test_returns_zero_for_clean_message(
        self, message_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = message_file("feat: clean subject\n\n- short bullet one\n")
        code = check_commit_message_lines.main([str(path)])
        assert code == 0
        assert capsys.readouterr().out.strip() == ""

    def test_returns_one_and_lists_offenders(
        self, message_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        long_body = "- " + "x" * 120
        path = message_file(f"subject under limit\n\n{long_body}\n")
        code = check_commit_message_lines.main([str(path)])
        captured = capsys.readouterr()
        assert code == 1
        assert "exceed 80 characters" in captured.out
        assert re.search(r"line\s+3 \(", captured.out) is not None
        assert "commit-messages.instructions.md" in captured.out

    def test_uses_env_var_when_no_argument(
        self,
        message_file: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = message_file("bad " + "q" * 90)
        monkeypatch.setenv("COMMIT_MSG_FILE", str(path))
        code = check_commit_message_lines.main([])
        captured = capsys.readouterr()
        assert code == 1
        assert "exceed 80 characters" in captured.out

    def test_missing_file_returns_one_with_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "does-not-exist"
        code = check_commit_message_lines.main([str(missing)])
        captured = capsys.readouterr().out
        assert code == 1
        assert "ERROR" in captured

    def test_no_source_at_all_returns_one(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("COMMIT_MSG_FILE", raising=False)
        code = check_commit_message_lines.main([])
        captured = capsys.readouterr().out
        assert code == 1
        assert "no commit message file provided" in captured
