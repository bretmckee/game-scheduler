<!-- markdownlint-disable-file -->

# Task Research Notes: Unit Test Quality Audit via Mutation Testing

## Research Executed

### File Analysis

- `pyproject.toml`
  - `[tool.mutmut]` section added with `paths_to_mutate`, `tests_dir`, `also_copy`
  - `also_copy = ["services", "shared"]` required: mutmut sandboxes source into `mutants/` and removes the original from `sys.path`; without this, imports fail
  - Config is overwritten before each `mutmut run` to point at the current target file

- `tests/unit/shared/messaging/test_consumer.py`
  - 15 tests, 32 mock setups, **zero** `assert_called_with`/`assert_called_once_with`-style assertions
  - Mocks are set up with return values but call arguments never verified
  - mutmut result: 91/136 survived (**67% survival** — worst measured)

- `tests/unit/services/retry/test_retry_daemon_unit.py`
  - 31 tests
  - mutmut result: 245/438 raw survivors; categorized as **96 logic / 97 other string / 52 telemetry string**
  - Logic survival rate: 22%

- `tests/unit/services/bot/test_guild_sync.py`
  - 23 tests
  - mutmut result: 77/238 survived (32% survival); ~50 estimated logic survivors

- `tests/unit/services/api/services/test_channel_resolver.py`
  - 26 tests (fully analyzed)
  - mutmut result: 32/185 survived (17% survival), all 32 survivors documented by type

- `tests/unit/services/api/services/test_guild_service.py` + `tests/unit/api/services/test_guild_service_channel_refresh.py`
  - 10 tests total
  - mutmut result: 12/66 survived (18%), 5 uncovered

- `services/api/services/calendar_export.py`
  - CC=12 for `_create_event`; **zero unit tests** — mutmut cannot run

- `.venv/lib/python3.13/site-packages/mutmut/file_mutation.py`
  - `pragma_no_mutate_lines()`: only filtering mechanism is `# pragma: no mutate` per line
  - `MutationVisitor._skip_node_and_children()`: skips type annotations, decorated functions, non-simple default args
  - Triple-quoted strings are skipped by `operator_string` (assumed docstrings)
  - No global config key to disable string mutations

- `.venv/lib/python3.13/site-packages/mutmut/node_mutation.py`
  - `operator_string`: generates 3 mutations per single-quoted string literal: `"XX<val>XX"`, lowercase, uppercase
  - `mutation_operators` list is hardcoded — no runtime filtering by operator type
  - String mutations survive whenever tests do not assert on the exact string value passed to a function

- `.venv/lib/python3.13/site-packages/mutmut/__main__.py`
  - `SourceFileMutationData.load()`: reads per-file JSON from `mutants/<path>.json`, contains `exit_code_by_key`
  - `status_by_exit_code[0] == "survived"`, `status_by_exit_code[1] == "killed"`
  - `get_diff_for_mutant(name)`: calls `read_mutants_module(path)` (parses the entire mutated file) + `read_original_function` + `read_mutant_function` per call — O(N) file parses for N mutants from the same file
  - `walk_source_files()`: iterates configured source paths; used to enumerate all mutant data files

- `scripts/mutmut-logic-survivors.py` (created this session)
  - Filters string-only mutations from survivor list using `is_string_only_mutation(diff)`
  - Key optimization: parses each mutated source file **once** per file, not once per mutant
  - Result: 2m35s → 1.2s (125× speedup) for 245 retry_daemon survivors
  - `--summary` flag prints counts only; default prints full diffs

### Code Search Results

- `assert_called_with|assert_called_once_with|call_args|assert_any_call`
  - 31 test files have mocks but zero call-verification assertions — identified at session start
  - These files exercise code paths but cannot detect wrong argument values

- `# pragma: no mutate`
  - Zero occurrences in the codebase — no existing suppression pragmas

- `operator_string` in mutmut source
  - Hardcoded in `mutation_operators` list — confirmed no config hook to disable globally

### External Research

- mutmut 3.5.0 source code (installed package)
  - String mutation suppression: only `# pragma: no mutate` per line — no `pyproject.toml` key
  - `operator_string` skips triple-quoted strings, but not single-quoted logging format strings
  - `get_diff_for_mutant` prints to stdout as a side effect (uses `print(f'# {mutant_name}: {status}')`) — must redirect stdout when calling from a script

### Project Conventions

- Standards referenced: `python.instructions.md` (type hints, uv, pytest), `test-driven-development.instructions.md`
- Package manager: `uv`; run commands with `uv run`
- Test runner: `pytest` with `asyncio_mode = "auto"`

## Key Discoveries

### Root Cause of Original Bug

Reversed positional arguments to a mocked function. Tests confirmed the function was called but never verified what arguments were passed. This is the canonical weakness that `assert_called_once_with` fixes and that mutmut's `operator_arg_removal` mutation (arg → `None`, or arg order swap via removal + reposition) detects.

### Mutation Testing Mechanics

mutmut 3 works by:

1. Copying source into `mutants/` directory and removing original from `sys.path`
2. Generating multiple mutations per function using libcst AST transformations
3. Running the test suite against each mutation; exit code 0 = survived (tests didn't catch it)
4. Storing results per source file in JSON alongside the mutated source

String mutations (`operator_string`) produce 3 variants per string literal: XX-wrap, lowercase, uppercase. These survive whenever:

- The string is a log message and tests don't assert on logger call args
- The string is a metric name/description and telemetry is not asserted
- The string is an error dict key that tests don't verify

### Survivor Categories

From analysis of retry_daemon (245 raw survivors):

| Category         | Count | Meaning                                                            |
| ---------------- | ----- | ------------------------------------------------------------------ |
| LOGIC            | 96    | Real test gaps — operators, arg values, control flow               |
| OTHER_STRING     | 97    | String literals not in telemetry (often error messages, dict keys) |
| TELEMETRY_STRING | 52    | OTEL metric names, descriptions, units                             |

The OTHER_STRING category partially overlaps with real test gaps (e.g. error dict keys that should be verified) but also includes noise (log message wording). The `is_string_only_mutation()` function in the new script catches both using the XX-prefix and case-only-change heuristics.

### Logging Assertion Pattern

For error handling code, the correct balance is:

- Verify the logger **was called** and at the **right level**: `mock_log.error.assert_called_once()`
- Verify **variable arguments** (the exception, the object): use `unittest.mock.ANY` for the message string
- Do NOT assert on exact message text — string mutations then die without making tests brittle

```python
# Correct pattern
mock_logger.error.assert_called_once_with(ANY, caught_exception)
# not: assert_called_once_with("Error closing publisher: %s", e)
```

### mutmut Config Requirement

Every `mutmut run` requires `also_copy = ["services", "shared"]` in `[tool.mutmut]`. Without it, imports from other packages in the `services/` and `shared/` source roots fail inside the sandboxed `mutants/` directory.

### Performance Fix for Results Script

`get_diff_for_mutant()` calls `read_mutants_module(path)` which parses the entire mutated file (can be 10k+ lines for retry_daemon) via libcst. Called per-mutant, this is O(N) file parses. The fix: group mutants by source path, parse once per file, pass the cached `cst.Module` to `read_original_function`/`read_mutant_function`.

## Recommended Approach

**Use the post-run filter script (`scripts/mutmut-logic-survivors.py`) as the standard workflow** — do not add `# pragma: no mutate` to source files.

Workflow for each target file:

1. Update `[tool.mutmut]` in `pyproject.toml` to point at the target
2. Run `uv run mutmut run`
3. Run `uv run scripts/mutmut-logic-survivors.py` to see logic-only survivors
4. Fix tests to kill the logic survivors (add `assert_called_once_with`, add missing test cases)
5. Re-run mutmut to verify the survival count drops

For logger assertions: assert that the logger method was called (`mock_log.error.assert_called_once_with(ANY, ...)`) — this kills arg-removal mutations without asserting on message text.

## Implementation Guidance

- **Objectives**: Improve unit test effectiveness so argument-swap bugs like the original are caught
- **Key Tasks**:
  - Fix `test_consumer.py` first (67% survival — worst; 32 mocks with zero call verification)
  - Fix `test_guild_sync.py` second (32% survival)
  - Fix `test_retry_daemon_unit.py` third (96 real logic survivors after string filtering)
  - Fix `test_channel_resolver.py` and `test_guild_service.py` last (already below 20%)
  - Write first unit tests for `calendar_export.py` (zero coverage, CC=12)
- **Dependencies**: mutmut 3.5.0 (already installed), `scripts/mutmut-logic-survivors.py` (created)
- **Success Criteria**: Logic survival rate below 10% for all measured files
