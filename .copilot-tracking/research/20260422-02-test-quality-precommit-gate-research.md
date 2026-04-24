<!-- markdownlint-disable-file -->

# Task Research Notes: Zero-Assertion Test Gate (Pre-commit)

## Research Executed

### File Analysis

- `.pre-commit-config.yaml`
  - Hooks in order: copyright, ruff-format, ruff, prettier, eslint, python-compile, mypy, pytest-random, pytest-coverage, diff-coverage, frontend-build, typescript, vitest-coverage, diff-coverage-frontend, complexipy, lizard-typescript, jscpd-generate, jscpd-diff, check-lint-suppressions
  - `check-lint-suppressions` (line 238) is the last always-run hook — new hook goes here
  - Hook pattern for custom Python scripts: `language: python`, `pass_filenames: false`, `entry: python scripts/<name>.py`
  - `diff-coverage` hook uses `git diff --cached --name-only --diff-filter=ACM` to scope to staged files — same pattern for diff-aware assertion check

- `tests/unit/` (fresh AST scan, April 22, 2026)
  - **90 test functions with zero assertions** across the unit test suite
  - Zero assertions means: no `assert` statement, no `assert_called*` / `assert_awaited*`, no `pytest.raises`
  - Concentrated in `tests/unit/bot/events/` (most violations)
  - Full list captured below in Key Discoveries

- `scripts/check_lint_suppressions.py`
  - Model for the new checker: reads staged files via `git diff --cached`, pure Python, `pass_filenames: false`
  - Uses `subprocess.run(["git", "diff", "--cached", "--name-only", ...])` for staged file enumeration

### Code Search Results

- `assert_called|assert_awaited|assert_any_call|assert_not_called` in `tests/unit/`
  - 27 non-conftest test files have mocks but zero call-verification assertions (measured earlier in session)
  - These tests verify that code runs without error but cannot detect wrong argument values or missing calls

- `pytest.raises` usage
  - Present in many test files — counts as a valid assertion for purposes of this gate

### External Research

- Python `ast` module docs
  - `ast.Assert` node: represents `assert <expr>` statements
  - `ast.Call` node: represents function calls — attribute name check catches `assert_called_*` family
  - `ast.With` node with `pytest.raises(...)` as context manager: check `isinstance(item, ast.withitem)` where `item.context_expr` is a `pytest.raises` call

## Key Discoveries

### Zero-Assertion Test Functions (90 total, April 22, 2026)

Top offending files:

- `tests/unit/bot/events/test_handlers_game_events.py` — largest concentration
- `tests/unit/bot/events/test_handlers_lifecycle_events.py`
- Other bot and shared test files

These tests typically look like:

```python
async def test_handle_game_created_game_not_found(mock_deps):
    mock_deps.game_service.get_game.return_value = None
    await handler.handle_game_created({"game_id": "123"})
    # no assertion — only verifies no exception raised
```

They exercise code paths but cannot detect:

- Wrong argument values passed to mocked dependencies
- Missing calls that should have been made
- Extra calls that should not have been made

### AST Assertion Detection

Five node types constitute a valid assertion:

```python
def has_assertion(func_node: ast.AST) -> bool:
    for node in ast.walk(func_node):
        # assert statement
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            attr = None
            if isinstance(node.func, ast.Attribute):
                attr = node.func.attr
            elif isinstance(node.func, ast.Name):
                attr = node.func.id
            # mock call-verification assertions
            if attr and any(attr.startswith(p) for p in [
                'assert_called', 'assert_awaited',
                'assert_any_call', 'assert_not_called',
            ]):
                return True
            # pytest.raises context manager (also appears as call)
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'raises':
                return True
    return False
```

### Diff-Aware Scoping (Phase 1 Rollout)

To avoid blocking all 90 existing violations on day one, the hook should only check test functions that are **new or modified** in the staged diff.

Strategy:

1. Get staged test files: `git diff --cached --name-only --diff-filter=ACM | grep 'tests/.*\.py'`
2. For each staged test file, parse with `ast` and find all `test_*` functions
3. Get added/modified line ranges from the diff: `git diff --cached -U0 <file>`
4. Only check functions whose `node.lineno` falls within added/modified line ranges
5. Report violations only for functions in the diff

This is the same scoping strategy used by `diff-cover` and the existing `diff-coverage` hook.

### Phase 2 (Full Mode)

Once the 90 existing violations are cleaned up, the hook switches to checking all `test_*` functions in staged files — no diff scoping needed. This can be a CLI flag: `--diff-only` for Phase 1, default (no flag) for Phase 2.

### Escape Hatch

Some tests genuinely test "no exception is raised" without needing an explicit assertion. For these, use an explicit `assert True` or `assert result is None` to make the intent visible. No `# noqa`-style bypass is warranted — if the test has no assertion it should not exist.

### Implementation: `scripts/check_test_assertions.py`

```python
#!/usr/bin/env python3
"""Check that all test functions contain at least one assertion."""
import ast
import subprocess
import sys
from pathlib import Path


def get_staged_test_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=True,
    )
    return [
        Path(p) for p in result.stdout.splitlines()
        if p.startswith("tests/") and p.endswith(".py")
    ]


def get_modified_line_ranges(filepath: Path) -> set[int]:
    result = subprocess.run(
        ["git", "diff", "--cached", "-U0", str(filepath)],
        capture_output=True, text=True, check=True,
    )
    lines: set[int] = set()
    for line in result.stdout.splitlines():
        if line.startswith("@@"):
            # @@ -old +new,count @@
            parts = line.split("+")[1].split("@@")[0].strip()
            start, _, length = parts.partition(",")
            start_n = int(start)
            count = int(length) if length else 1
            lines.update(range(start_n, start_n + count))
    return lines


def has_assertion(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            attr = None
            if isinstance(node.func, ast.Attribute):
                attr = node.func.attr
            elif isinstance(node.func, ast.Name):
                attr = node.func.id
            if attr and any(attr.startswith(p) for p in [
                "assert_called", "assert_awaited",
                "assert_any_call", "assert_not_called",
            ]):
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr == "raises":
                return True
    return False


def check_file(filepath: Path, diff_only: bool) -> list[tuple[int, str]]:
    modified_lines = get_modified_line_ranges(filepath) if diff_only else None
    tree = ast.parse(filepath.read_text())
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if diff_only and modified_lines and node.lineno not in modified_lines:
            continue
        if not has_assertion(node):
            violations.append((node.lineno, node.name))
    return violations


def main() -> int:
    diff_only = "--diff-only" in sys.argv
    files = get_staged_test_files()
    found_any = False
    for filepath in files:
        try:
            violations = check_file(filepath, diff_only=diff_only)
        except (SyntaxError, OSError):
            continue
        for lineno, name in violations:
            print(f"{filepath}:{lineno}: {name} has no assertions")
            found_any = True
    return 1 if found_any else 0


if __name__ == "__main__":
    sys.exit(main())
```

### Pre-commit Hook Definition (Phase 1)

Insert after `check-lint-suppressions` in the local hooks section:

```yaml
# Block test functions with zero assertions in staged test files
- id: check-test-assertions
  name: Check test functions have assertions
  entry: python scripts/check_test_assertions.py --diff-only
  language: python
  pass_filenames: false
  files: ^tests/.*\.py$
```

For Phase 2 (after cleanup), remove `--diff-only` from `entry`.

## Recommended Approach

**Phase 1**: Add `scripts/check_test_assertions.py` with `--diff-only` mode. This blocks new violations without touching the 90 existing ones.

**Cleanup**: Fix the 90 existing zero-assertion tests — most need either `mock.assert_called_once()` or `assert result == expected`.

**Phase 2**: Remove `--diff-only` to enforce on all staged test files.

## Implementation Guidance

- **Objectives**: Prevent new "coverage theater" tests from entering the codebase
- **Key Tasks**:
  1. Create `scripts/check_test_assertions.py` (content above)
  2. Add `check-test-assertions` hook to `.pre-commit-config.yaml` (Phase 1 config above)
  3. Clean up the 90 existing zero-assertion test functions
  4. Remove `--diff-only` flag once existing violations are resolved (Phase 2)
- **Dependencies**: Python stdlib only (`ast`, `subprocess`) — no new packages
- **Success Criteria**: `pre-commit run check-test-assertions` exits 0 on main branch with no `--diff-only` flag
