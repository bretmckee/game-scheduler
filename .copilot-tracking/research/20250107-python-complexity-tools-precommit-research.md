<!-- markdownlint-disable-file -->
# Task Research Notes: Python Complexity Measurement Tools for Pre-Commit Integration

## Research Executed

### File Analysis
- `.pre-commit-config.yaml`
  - Current pre-commit setup with ruff, mypy, pytest hooks
  - fail_fast: true, python3.13
  - No complexity checks initially configured
- `pyproject.toml` (lines 65-90)
  - Ruff configuration with select rules ["E", "F", "I", "N", "W", "B", "C4", "UP", "PLR2004", "PLC0415"]
  - C901 (McCabe complexity) not initially enabled
  - line-length=100, target-version="py313"

### Code Search Results
- pyproject.toml search for C901/mccabe
  - No matches initially - C901 not configured
- `.pre-commit-config.yaml` pre-commit hooks
  - Comprehensive setup already in place
  - Uses fail_fast strategy for quick feedback

### External Research
- Ruff C901 Documentation
  - Ruff supports C901 rule via mccabe plugin
  - Configuration: `[tool.ruff.lint.mccabe]` with `max-complexity` setting
  - Default max-complexity: 10
  - Configurable per-file via pyproject.toml
- Complexipy GitHub Repository
  - Rust-based cognitive complexity tool (not cyclomatic)
  - Supports: CLI, Python API, pre-commit hooks, VSCode extension, GitHub Actions
  - Pre-commit integration via separate repo: rohaquinlop/complexipy-pre-commit
  - Features: snapshot baselines, inline ignores (`# noqa: complexipy`), TOML config, JSON/CSV output
  - Measures cognitive complexity (focus on human readability, not just cyclomatic)
- Xenon
  - Monitoring tool based on radon
  - Pre-commit hook available in repo
  - Configuration uses letter grades (A-F) and thresholds
  - Based on radon's cyclomatic complexity engine
- Wily
  - Historical complexity tracking tool
  - Pre-commit plugin available
  - Compares against git revisions
  - Supports operators: mccabe, cyclomatic, maintainability, raw
- Radon
  - Comprehensive Python metrics tool
  - Metrics: cyclomatic complexity (McCabe), Halstead, maintainability index, raw (SLOC, LOC, comments)
  - Flake8 plugin available
- Flake8-Cognitive-Complexity
  - Flake8 extension for cognitive complexity
  - Error code: CCR001
  - Unmaintained (last update July 2020), Python 3.7 only

### Project Conventions
- Standards referenced:
  - `.github/instructions/python.instructions.md` - "Break down complex functions into smaller, more manageable functions"
  - Pre-commit setup with fail_fast: true for quick feedback
- Instructions followed:
  - Python 3.13 as target version
  - UV for package management
  - Ruff for linting/formatting

## Key Discoveries

### Project Structure
- Pre-commit framework already extensively used
- UV package manager in use (commands: `uv add`, `uv run`)
- Ruff ~0.9.0 configured
- Python 3.13 target version

### Available Python Complexity Tools

#### 1. Ruff (Built-in C901 - McCabe Complexity)
**Type**: Cyclomatic Complexity (McCabe)

**Metrics Available**:
- Cyclomatic complexity only (per function/method)

**Pre-commit Integration**:
```yaml
# Already in .pre-commit-config.yaml
- repo: local
  hooks:
    - id: ruff-check
      name: ruff check
      entry: uv run ruff check --fix
      language: system
      types: [python]
```

**Configuration**:
```toml
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "UP", "PLR2004", "PLC0415", "C901"]

[tool.ruff.lint.mccabe]
max-complexity = 25  # Set to prevent regressions
```

**Pros**:
- Already installed and configured in project
- Zero additional dependencies
- Fast (Rust-based)
- Integrates with existing ruff check workflow
- Simple to enable (just add C901 to select list)

**Cons**:
- Only cyclomatic complexity (not cognitive, maintainability index, or LOC)
- Per-function only (no per-class or per-module aggregation)
- No diff-based checking (checks entire file)
- No baseline/snapshot support

**Diff-Based Checking**: Not natively supported

---

#### 2. Complexipy
**Type**: Cognitive Complexity

**Metrics Available**:
- Cognitive complexity (per-function and per-line breakdown)
- Total file complexity

**Pre-commit Integration**:
```yaml
repos:
  - repo: https://github.com/rohaquinlop/complexipy-pre-commit
    rev: v4.2.0
    hooks:
      - id: complexipy
        args: ['--max-complexity-allowed', '49']
```

**Configuration**:
```toml
# pyproject.toml
[tool.complexipy]
paths = ["services", "shared"]
max-complexity-allowed = 49  # Set to prevent regressions
exclude = []
```

**Pros**:
- Rust-based (blazingly fast)
- Measures cognitive complexity (human-focused, not just cyclomatic)
- Snapshot/baseline support for tracking regressions
- Inline ignores: `# noqa: complexipy`
- JSON/CSV output for reporting
- Python API available
- Active development (v4.2.0)
- VSCode extension and GitHub Actions available

**Cons**:
- Additional dependency (though lightweight)
- Cognitive complexity only (no cyclomatic, maintainability index, or Halstead)
- No diff-based checking (checks entire files)
- Separate pre-commit repo needed

**Diff-Based Checking**: Not natively supported

---

#### 3. Xenon
**Type**: Cyclomatic Complexity (McCabe) - Monitoring Tool

**Metrics Available**:
- Cyclomatic complexity (via radon)
- Block-level, module-level, and average complexity
- Letter grades (A-F)

**Pre-commit Integration**:
```yaml
repos:
  - repo: https://github.com/rubik/xenon
    rev: v0.9.0
    hooks:
      - id: xenon
        args: ['--max-absolute=B', '--max-modules=B', '--max-average=A']
```

**Configuration**: Via command-line args only (no config file)

**Letter Grades**:
- A: 1-5 (low complexity)
- B: 6-10 (moderate)
- C: 11-20 (complex)
- D: 21-30 (very complex)
- E: 31-40 (extremely complex)
- F: 41+ (unmaintainable)

**Pros**:
- Built on radon (well-established tool)
- Multiple thresholds (block, module, average)
- Intuitive letter grading system
- Direct pre-commit hook in main repo

**Cons**:
- Only cyclomatic complexity
- No config file support (args only)
- Older tool
- No snapshot/baseline support
- No diff-based checking

**Diff-Based Checking**: Not supported

---

#### 4. Radon
**Type**: Comprehensive Metrics Suite

**Metrics Available**:
- Cyclomatic complexity (McCabe)
- Halstead metrics (volume, difficulty, effort, time, bugs)
- Maintainability index
- Raw metrics (SLOC, LOC, LLOC, comments, blank lines)

**Pre-commit Integration**: No official hook, requires custom local hook

**Pros**:
- Most comprehensive metrics
- Well-established, mature tool
- Multiple commands for different metrics
- Flexible output formats
- Per-file and per-function granularity

**Cons**:
- No official pre-commit hook
- Requires custom local hook setup
- No config file support
- No snapshot/baseline support
- No diff-based checking
- Separate commands for each metric type

**Diff-Based Checking**: Not supported

---

#### 5. Wily
**Type**: Historical Complexity Tracking

**Metrics Available**:
- All radon metrics (cyclomatic, maintainability, raw, Halstead)
- Historical trend tracking via git
- Operators: mccabe, cyclomatic, maintainability, raw

**Pre-commit Integration**:
```yaml
repos:
  - repo: local
    hooks:
      - id: wily
        name: wily complexity check
        entry: wily diff
        verbose: true
        language: python
        additional_dependencies: [wily]
```

**Pros**:
- Historical trend analysis
- All radon metrics available
- Git integration (compares against HEAD^1, master, etc.)
- Rich visualization
- Snapshot/baseline via `.wily/` cache
- CI/CD friendly

**Cons**:
- Requires building `.wily/` cache first
- More complex setup
- Heavier dependency
- Pre-commit hook requires cache to exist
- Not suitable for quick per-commit checks

**Diff-Based Checking**: Yes - compares against git revisions (`wily diff -r HEAD^1`)

---

#### 6. Flake8-Cognitive-Complexity
**Type**: Cognitive Complexity (Flake8 Plugin)

**Status**: Not recommended - unmaintained, Python 3.7 only

---

### Diff-Based Checking Capabilities

**Native Support**:
- **Wily**: Full support - compares against git revisions

**No Native Support** (checks entire files):
- Ruff C901
- Complexipy
- Xenon
- Radon
- Flake8-Cognitive-Complexity

**Workaround**: Pre-commit framework provides file-level filtering (only runs on staged files)

## Recommended Approach

**Implementation**: Enable Both Ruff C901 and Complexipy

**Rationale**:
1. **Complementary Metrics**: Cyclomatic (paths) + Cognitive (understandability)
2. **Zero Friction**: Both integrate with existing pre-commit workflow
3. **Fast**: Both are Rust-based with minimal performance impact
4. **Progressive Improvement**: Set thresholds to prevent regressions, then lower as functions are refactored

**Configuration**:
```toml
# pyproject.toml
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "UP", "PLR2004", "PLC0415", "C901"]

[tool.ruff.lint.mccabe]
max-complexity = 25  # Current max: 24, will lower as we refactor

[tool.complexipy]
max-complexity-allowed = 49  # Current max: 48, will lower as we refactor
paths = ["services", "shared"]
exclude = []
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/rohaquinlop/complexipy-pre-commit
    rev: v4.2.0
    hooks:
      - id: complexipy
        args: ['--max-complexity-allowed', '49']
```

## Actual Results from Codebase

### Cyclomatic Complexity (C901) - Threshold: 25
- **Total Violations**: 20 functions (at threshold 10)
- **Highest Score**: 24 - `GameService::create_game()`
- **Range**: 11-24

### Cognitive Complexity (Complexipy) - Threshold: 49
- **Total Violations**: 39 functions (at threshold 10)
- **Highest Score**: 48 - `GameService::create_game()`
- **Total Codebase Complexity**: 1,799 points across 305 files
- **Range**: 11-48

### Notable Comparisons
Functions where cognitive >> cyclomatic:
- `create_game()`: Cognitive=48, Cyclomatic=24 (2x worse)
- `resolve_display_names_and_avatars()`: Cognitive=27, Cyclomatic=12 (2.25x worse)
- `RetryDaemon::_process_event()`: Cognitive=39 (not flagged by C901)

## Implementation Guidance

### Objectives
1. Prevent introduction of overly complex functions
2. Provide immediate feedback during development
3. Enable progressive refactoring without breaking existing code
4. Track both execution complexity and cognitive load

### Key Tasks

**Phase 1: Enable Complexity Checking** ✅ COMPLETED
1. Add C901 to ruff.lint.select in pyproject.toml
2. Add complexipy to pre-commit config
3. Set thresholds 1 above current max (prevent regressions)
4. Verify all checks pass

**Phase 2: Refactor Highest Complexity Functions** (Next)
1. `GameService::create_game()` - 344 lines, cognitive: 48, cyclomatic: 24
2. `RetryDaemon::_process_event()` - cognitive: 39
3. `DisplayNameResolver::resolve_display_names_and_avatars()` - cognitive: 27

**Phase 3: Progressive Threshold Reduction**
- After each refactoring, lower thresholds incrementally
- Target: cyclomatic ≤ 15, cognitive ≤ 20

### Dependencies
- Ruff ~0.9.0 ✅ (already installed)
- Complexipy v4.2.0+ ✅ (added via pre-commit)
- Pre-commit framework ✅ (already configured)

### Success Criteria
1. Pre-commit hooks run successfully on all commits ✅
2. No functions exceed threshold (prevent regressions) ✅
3. Progressive refactoring lowers thresholds over time (in progress)
4. Team understands complexity metrics and accepts thresholds
