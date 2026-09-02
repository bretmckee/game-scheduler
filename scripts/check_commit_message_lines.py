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


"""Pre-commit commit-msg hook that enforces maximum commit message line length.

Every non-comment line of the commit message must fit within MAX_LINE_LENGTH
characters so messages stay readable in `git log`, terminal panes, and GitHub.

The commit message file path arrives as the first positional argument (the
standard commit-msg contract) or via the COMMIT_MSG_FILE environment variable.
Comment lines starting with '#' are ignored because git strips them from the
final message before it is stored.

Bypassing this check requires explicit approval per the quality-check override
policy (`SKIP=check-commit-message-lines` plus `--no-verify` handling by the
scripts/wrappers/git wrapper).
"""

import os
import sys
from collections.abc import Sequence

MAX_LINE_LENGTH = 80
MAX_REPORTED_VIOLATIONS = 25

_HOOK_NAME = "commit-message-lines"


def _find_violations(
    message_lines: list[str], max_length: int = MAX_LINE_LENGTH
) -> list[tuple[int, str]]:
    """Return (line_number, line) pairs for comment-free lines exceeding max_length."""
    violations: list[tuple[int, str]] = []
    for number, line in enumerate(message_lines, start=1):
        if line.lstrip().startswith("#"):
            continue
        stripped = line.rstrip()
        if len(stripped) > max_length:
            violations.append((number, stripped))
    return violations


def _truncate(text: str, width: int = 60) -> str:
    """Shorten a line for display without changing its measured length."""
    return text if len(text) <= width else f"{text[: width - 3]}..."


def check_commit_message_file(
    path: str, max_length: int = MAX_LINE_LENGTH
) -> tuple[list[tuple[int, str]], str]:
    """Read a commit message file and return (violations, raw_message_text)."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        message = handle.read()
    lines = message.splitlines()
    return _find_violations(lines, max_length), message


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns 0 when all lines fit the limit, 1 otherwise."""
    args = list(sys.argv[1:]) if argv is None else list(argv)

    if args:
        path = args[0]
    elif "COMMIT_MSG_FILE" in os.environ:
        path = os.environ["COMMIT_MSG_FILE"]
    else:
        print(f"{_HOOK_NAME}: ERROR: no commit message file provided.")
        return 1

    try:
        violations, _ = check_commit_message_file(path)
    except OSError as exc:
        print(f"{_HOOK_NAME}: ERROR: could not read {path}: {exc}")
        return 1

    if not violations:
        return 0

    reported = violations[:MAX_REPORTED_VIOLATIONS]
    omitted = len(violations) - len(reported)
    print(f"{_HOOK_NAME}: FAIL — {len(violations)} line(s) exceed {MAX_LINE_LENGTH} characters:\n")
    for number, line in reported:
        print(f"  line {number:>4d} ({len(line):>3d} chars): {_truncate(line)}")
    if omitted > 0:
        print(f"  ... and {omitted} more line(s)")
    print(
        "\nWrap every subject and body line to at most "
        f"{MAX_LINE_LENGTH} characters (see .github/instructions/commit-messages.instructions.md)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
