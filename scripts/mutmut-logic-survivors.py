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


"""Show logic (non-string-literal) survivors from the most recent mutmut run.

Usage:
    uv run scripts/mutmut-logic-survivors.py           # diffs for all logic survivors
    uv run scripts/mutmut-logic-survivors.py --summary # counts only

String-only mutations (XX-wrap, lower, upper produced by operator_string) are
excluded because they require tests to assert on log message wording, which is
brittle and low-value.
"""

import sys
from difflib import unified_diff
from pathlib import Path

import libcst as cst
from mutmut.__main__ import (
    SourceFileMutationData,
    ensure_config_loaded,
    read_mutant_function,
    read_original_function,
    status_by_exit_code,
    walk_source_files,
)


def get_survived_by_path() -> dict[Path, list[str]]:
    """Return survived mutant names grouped by their source path."""
    result: dict[Path, list[str]] = {}
    for path in walk_source_files():
        if not str(path).endswith(".py"):
            continue
        m = SourceFileMutationData(path=path)
        m.load()
        survived = [
            k for k, v in m.exit_code_by_key.items() if status_by_exit_code[v] == "survived"
        ]
        if survived:
            result[path] = survived
    return result


def compute_diff(module: cst.Module, name: str, path: str) -> str:
    """Compute the unified diff for one mutant using an already-parsed module."""
    orig_code = cst.Module([read_original_function(module, name)]).code.strip()
    mutant_code = cst.Module([read_mutant_function(module, name)]).code.strip()
    return "\n".join(
        unified_diff(
            orig_code.splitlines(),
            mutant_code.splitlines(),
            fromfile=path,
            tofile=path,
            lineterm="",
        )
    )


def is_string_only_mutation(diff: str) -> bool:
    def changed_lines(prefix: str, exclude: str) -> list[str]:
        return [
            line[1:]
            for line in diff.splitlines()
            if line.startswith(prefix) and not line.startswith(exclude)
        ]

    plus_lines = changed_lines("+", "+++")
    minus_lines = changed_lines("-", "---")

    if not plus_lines:
        return False

    # operator_string wraps content as "XX<original>XX"
    if any('"XX' in line or "'XX" in line for line in plus_lines):
        return True

    # operator_string also lowercases or uppercases content; lines differ only in case
    return len(plus_lines) == len(minus_lines) and all(
        p.lower() == m.lower() and p != m for p, m in zip(plus_lines, minus_lines, strict=True)
    )


def main() -> None:
    ensure_config_loaded()

    summary_only = "--summary" in sys.argv

    survived_by_path = get_survived_by_path()
    if not survived_by_path:
        print("No survived mutants found.")
        return

    logic: list[tuple[str, str]] = []
    string_count = 0

    for path, names in survived_by_path.items():
        # Parse the mutated file once per source file rather than once per mutant.
        mutants_path = Path("mutants") / path
        with open(mutants_path, encoding="utf-8") as f:
            module = cst.parse_module(f.read())
        path_str = str(path)

        for name in names:
            diff = compute_diff(module, name, path_str)
            if is_string_only_mutation(diff):
                string_count += 1
            else:
                logic.append((name, diff))

    if not summary_only:
        for name, diff in logic:
            print(f"\n{'=' * 60}")
            print(f"# {name}")
            print(diff)

    print(f"\nLogic survivors: {len(logic)}  |  String-only (filtered): {string_count}")


if __name__ == "__main__":
    main()
