<!-- markdownlint-disable-file -->

# Task Research Notes: Per-Function Mutation Testing Gate (CI/CD)

## Research Executed

### File Analysis

- `pyproject.toml` — `[tool.mutmut]` section (experiment artifact, April 21, 2026)
  - Current: `paths_to_mutate = ["services/api/services/channel_resolver.py"]`
  - Production value: `paths_to_mutate = ["services/", "shared/"]`
  - `also_copy = ["services", "shared", "scripts"]` — required because `tests/unit/` imports from `scripts/`
  - `tests_dir = ["tests/unit"]`

- `mutants/services/api/services/channel_resolver.py.meta` (experiment artifact)
  - 185 mutant keys, all with results after two full runs
  - Key format: `services.api.services.channel_resolver.xǁChannelResolverǁresolve__mutmut_1`
  - All 185 keys covered by per-function wildcards (verified: 185/185 match rate)

- `mutants/mutmut-stats.json`
  - Keys: `tests_by_mangled_function_name`, `duration_by_test`
  - Persists between runs; explains why run 2 (27s) is faster than run 1 (55s) — stats collection is skipped, not test execution

- `.venv/lib/python3.13/site-packages/mutmut/trampoline_templates.py`
  - `CLASS_NAME_SEPARATOR = 'ǁ'`
  - `mangle_function_name(name, class_name)`: class methods → `xǁ{class}ǁ{method}`, top-level → `x_{func}`
  - This is the exact format needed to build MUTANT_NAMES wildcards

- `.venv/lib/python3.13/site-packages/mutmut/__main__.py`
  - MUTANT_NAMES filtering: `fnmatch.fnmatch(key, mutant_name)` — standard Unix glob matching
  - `mutmut run 'services.api.services.channel_resolver.xǁChannelResolverǁresolve__mutmut*'` runs only that method's mutants
  - Multiple space-separated wildcards are accepted on the command line

- `.github/workflows/ci-cd.yml`
  - `python-unit-tests` job (line 148): `runs-on: ubuntu-latest`, uses `astral-sh/setup-uv@v8.0.0`, Python 3.13
  - `build-test-publish` gate (line 283): `needs: [code-quality, python-unit-tests, ...]` — mutation-testing job should be added here
  - PR-only jobs pattern: `if: github.event_name == 'pull_request'` (used by diff-coverage)

### Code Search Results

- `MUTANT_NAMES` in mutmut source
  - `create_mutants_for_file()`: when `source_mtime < mutant_mtime`, resets all `exit_code_by_key` to `None`
  - This means every completed run re-tests all mutants — mutmut's "incremental" only helps interrupted runs
  - The only way to skip functions is via MUTANT_NAMES filtering at run time, not via caching

- `ast.dump()` hash coverage test (run April 22, 2026)
  - `ast.dump(func_node)` for each class method / top-level function in `channel_resolver.py`
  - Wildcard `{module}.{mangled_name}__mutmut*` generated for each function
  - Result: **185/185 mutant keys matched** — 100% coverage, zero unmatched keys

### External Research

- mutmut 3.5.0 installed in `.venv`
  - No config key to filter by operator type — `# pragma: no mutate` per line is the only built-in suppression
  - `paths_to_mutate` accepts a list of paths (files or directories)
  - `also_copy` required for multi-root projects; value must include all source roots imported by tests

## Key Discoveries

### Why mutmut's Incremental Mode Does Not Help

`create_mutants_for_file()` checks `source_mtime < mutant_mtime`. If source is **unchanged**, it resets all `exit_code_by_key` to `None` so the run loop re-tests everything. This is not a cache — it's clearing stale results from a prior run. A fresh run always re-tests all mutants.

Timing confirmation:

- Run 1 (after `rm -rf mutants/`): **55.6s** — includes stats collection + all 185 mutant tests
- Run 2 (source unchanged): **27.4s** — skips stats collection only; still tests all 185 mutants

### MUTANT_NAMES Wildcard Format

| Function type  | Source signature           | Wildcard pattern               |
| -------------- | -------------------------- | ------------------------------ |
| Class method   | `class Foo: def bar(self)` | `my.module.xǁFooǁbar__mutmut*` |
| Top-level func | `def baz()`                | `my.module.x_baz__mutmut*`     |

The module name is the dotted import path derived from the file path: `services/api/services/foo.py` → `services.api.services.foo`.

### Per-Function AST Hash Wrapper Design

A wrapper script (`scripts/mutmut-smart-run.py`) that:

1. Reads `paths_to_mutate` from `[tool.mutmut]` in `pyproject.toml`
2. For each source file, parses with `ast.parse()` and extracts all class methods and top-level functions
3. For each function, computes `hashlib.sha256(ast.dump(func_node).encode()).hexdigest()`
4. Loads stored hashes from `mutants/function-hashes.json`
5. Identifies changed functions (hash differs or not in stored hashes)
6. Builds the MUTANT_NAMES wildcard list for changed functions only
7. Runs `uv run mutmut run <wildcard1> <wildcard2> ...`
8. On success, updates `mutants/function-hashes.json`

False positives (re-running when only a docstring changed) are **acceptable** — `ast.dump()` includes docstrings as `ast.Constant` nodes. The error rate is low and the consequence is only a slower run, never a missed mutation.

### Complete Hash Wrapper Implementation

```python
#!/usr/bin/env python3
"""Run mutmut only against functions whose AST has changed since the last run."""
import ast
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

HASH_DB = Path("mutants/function-hashes.json")
CLASS_SEP = "ǁ"


def mangle(name: str, class_name: str | None) -> str:
    if class_name:
        return f"x{CLASS_SEP}{class_name}{CLASS_SEP}{name}"
    return f"x_{name}"


def file_to_module(filepath: Path) -> str:
    return str(filepath)[:-3].replace("/", ".")


def get_function_hashes(filepath: Path) -> dict[str, str]:
    source = filepath.read_text()
    tree = ast.parse(source)
    module = file_to_module(filepath)
    hashes: dict[str, str] = {}
    class_method_ids: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_method_ids.add(id(item))
                    wildcard = f"{module}.{mangle(item.name, node.name)}__mutmut*"
                    hashes[wildcard] = hashlib.sha256(
                        ast.dump(item).encode()
                    ).hexdigest()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if id(node) not in class_method_ids:
                wildcard = f"{module}.{mangle(node.name, None)}__mutmut*"
                hashes[wildcard] = hashlib.sha256(
                    ast.dump(node).encode()
                ).hexdigest()

    return hashes


def get_paths_to_mutate() -> list[Path]:
    config = tomllib.loads(Path("pyproject.toml").read_text())
    raw = config.get("tool", {}).get("mutmut", {}).get("paths_to_mutate", [])
    paths = []
    for p in raw:
        path = Path(p)
        if path.is_dir():
            paths.extend(path.rglob("*.py"))
        elif path.is_file():
            paths.append(path)
    return paths


def main() -> int:
    stored: dict[str, str] = {}
    if HASH_DB.exists():
        stored = json.loads(HASH_DB.read_text())

    current: dict[str, str] = {}
    for filepath in get_paths_to_mutate():
        current.update(get_function_hashes(filepath))

    changed_wildcards = [
        wc for wc, h in current.items() if stored.get(wc) != h
    ]

    if not changed_wildcards:
        print("No functions changed — skipping mutmut run")
        return 0

    print(f"Running mutmut against {len(changed_wildcards)} changed function(s)")
    cmd = ["uv", "run", "mutmut", "run", *changed_wildcards]
    result = subprocess.run(cmd)

    if result.returncode == 0:
        HASH_DB.parent.mkdir(parents=True, exist_ok=True)
        merged = {**stored, **{wc: current[wc] for wc in changed_wildcards}}
        HASH_DB.write_text(json.dumps(merged, indent=2))

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
```

### `scripts/mutmut-logic-survivors.py` (needed, not yet created)

Filters string-only mutations from the survivor list. Referenced in the earlier research doc (`20260421-01-unit-test-quality-mutation-testing-research.md`) as "created this session" but **does not exist in the repo**. Must be created before the CI gate is useful.

Key logic: for each survived mutant, check if the diff shows only string literal changes (XX-prefix, casing). If so, classify as `STRING` rather than `LOGIC`. The CI gate should fail only on `LOGIC` survivors.

Performance note: parse each mutated source file once per file (not per mutant) by grouping survivors by source path. `get_diff_for_mutant()` in mutmut calls `read_mutants_module()` per call — O(N²) if not batched.

### Performance Data

From experiment on `channel_resolver.py` (185 mutants):

| Metric           | Value                          |
| ---------------- | ------------------------------ |
| First run (cold) | 55.6s                          |
| Mutant count     | 185                            |
| Time per mutant  | ~0.30s                         |
| Mutations/second | ~3.3                           |
| Stats-only phase | ~28s (saved on subsequent run) |

Projection for CI gate (PR touches 10 functions × 10 mutants/function = 100 mutants):

- Cold: ~30s
- With hash skipping (unchanged functions): scales to touched functions only

### CI Job Definition

```yaml
mutation-testing:
  name: Mutation Testing (changed functions)
  runs-on: ubuntu-latest
  needs: python-unit-tests
  if: github.event_name == 'pull_request'

  steps:
    - name: Checkout code
      uses: actions/checkout@v6
      with:
        fetch-depth: 0

    - name: Install uv
      uses: astral-sh/setup-uv@v8.0.0
      with:
        version: ${{ env.UV_VERSION }}

    - name: Set up Python
      run: uv python install 3.13

    - name: Install dependencies
      run: uv sync --extra dev

    - name: Restore mutmut hash database
      uses: actions/cache@v4
      with:
        path: mutants/function-hashes.json
        key: mutmut-hashes-${{ github.ref }}
        restore-keys: |
          mutmut-hashes-refs/heads/main

    - name: Run mutation testing (changed functions only)
      env:
        TESTING: true
      run: uv run python scripts/mutmut-smart-run.py

    - name: Filter logic survivors
      if: failure()
      run: uv run python scripts/mutmut-logic-survivors.py --summary

    - name: Save mutmut hash database
      if: success()
      uses: actions/cache/save@v4
      with:
        path: mutants/function-hashes.json
        key: mutmut-hashes-${{ github.ref }}
```

Also add `mutation-testing` to the `build-test-publish` needs list.

### `pyproject.toml` Production Config

The `[tool.mutmut]` section currently points only at `channel_resolver.py` (experiment artifact). Production value:

```toml
[tool.mutmut]
paths_to_mutate = ["services/", "shared/"]
tests_dir = ["tests/unit"]
also_copy = ["services", "shared", "scripts"]
```

`scripts/` in `also_copy` is required because `tests/unit/shared/test_check_commit_duplicates.py` imports from `scripts/check_commit_duplicates.py`.

## Recommended Approach

**Use `scripts/mutmut-smart-run.py` as a CI gate on PRs.**

The per-function AST hash database (`mutants/function-hashes.json`) cached in GitHub Actions (keyed by branch ref) means each PR run only tests functions changed in that branch. This keeps CI time proportional to change size rather than total codebase size.

Failure mode: if any survived mutants exist after a run, the step fails. The `mutmut-logic-survivors.py` filter script (which still needs to be created) provides actionable output by separating logic failures from string noise.

## Implementation Guidance

- **Objectives**: Automatically detect new test gaps in changed code on every PR
- **Key Tasks**:
  1. Create `scripts/mutmut-smart-run.py` (content above)
  2. Create `scripts/mutmut-logic-survivors.py` (filtering script, referenced in earlier research doc)
  3. Update `[tool.mutmut]` in `pyproject.toml` to point at `services/` and `shared/` (not just channel_resolver.py)
  4. Add `mutation-testing` job to `.github/workflows/ci-cd.yml` (definition above)
  5. Add `mutation-testing` to `build-test-publish` needs list
- **Dependencies**: mutmut 3.5.0 (installed), Python stdlib (`ast`, `hashlib`, `tomllib`), `uv`
- **Success Criteria**: PR touching `channel_resolver.py` runs only changed functions' mutants; hash DB caches across pushes to same branch
