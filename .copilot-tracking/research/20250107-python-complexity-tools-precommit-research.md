<!-- markdownlint-disable-file -->
# Task Research Notes: Multi-Language Cognitive Complexity Analysis Tools

**Last Updated**: 2026-01-28

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

---

## Multi-Language Complexity Tools Research (2026-01-28)

### Current Project Context

**Python**: ~15,000 lines (services/ and shared/)
- Using **Ruff C901** for cyclomatic complexity (threshold: 10)
- Using **complexipy** for cognitive complexity (threshold: 49)

**TypeScript/TSX**: ~3,400+ lines (frontend/)
- Currently no complexity checking

**Go**: None yet, but potential future addition

### Research Question
How does Lizard compare to Ruff for multi-language cyclomatic complexity analysis?

---

## Ruff C901 vs Lizard Comparison

### Ruff C901 (Current Python Tool)

**Type**: Python-only linter with cyclomatic complexity rule
**Metric**: McCabe cyclomatic complexity
**Integration**: Native to Ruff linter, already in pre-commit
**Configuration**:
```toml
[tool.ruff.lint]
select = ["C901"]

[tool.ruff.lint.mccabe]
max-complexity = 10
```

**Pros**:
- Already installed and configured
- Zero additional dependencies
- Extremely fast (Rust-based)
- Part of comprehensive linter (catches other issues too)
- Native pre-commit integration
- Precise Python parsing

**Cons**:
- Python-only
- No support for TypeScript, Go, or other languages
- Less detailed reporting than dedicated complexity tools
- No historical tracking or trend analysis

---

### Lizard (Multi-Language Alternative)

**Type**: Multi-language cyclomatic complexity analyzer
**Metric**: McCabe cyclomatic complexity (same as Ruff C901)
**Languages**:
- ✅ Python
- ✅ TypeScript (with TSX support)
- ✅ Go (Golang)
- Plus 25+ others (Java, C/C++, JavaScript, Ruby, Rust, Swift, etc.)

**Integration**: CLI tool, can be added to pre-commit
```yaml
- repo: https://github.com/terryyin/lizard
  rev: 1.20.0
  hooks:
    - id: lizard
      args: ['--CCN', '10', '--length', '1000']
```

**Pros**:
- **Multi-language support** - one tool for Python, TypeScript, Go
- Same metric as Ruff (McCabe cyclomatic complexity)
- Rich output formats: CLI, XML, HTML, CSV, JSON
- Additional metrics: NLOC, token count, parameter count, nesting depth
- Language-specific filtering: `lizard -l python services/` or `lizard -l typescript frontend/`
- Lightweight, single Python package
- Active maintenance (last update 2 weeks ago)
- Pre-commit hook available
- Can analyze all languages in one pass

**Cons**:
- Additional dependency to maintain
- Slower than Ruff (Python-based vs Rust-based)
- Less sophisticated Python parsing than Ruff
- Potential false positives/negatives compared to native language tools
- No auto-fix capabilities

---

## Detailed Feature Comparison

| Feature | Ruff C901 | Lizard |
|---------|-----------|--------|
| **Python** | ✅ Excellent | ✅ Good |
| **TypeScript** | ❌ | ✅ Yes (with TSX) |
| **Go** | ❌ | ✅ Yes |
| **Speed** | Extremely fast (Rust) | Fast (Python) |
| **Metric** | Cyclomatic | Cyclomatic (same) |
| **Pre-commit** | ✅ Native | ✅ Available |
| **NLOC** | ❌ | ✅ |
| **Token count** | ❌ | ✅ |
| **Nesting depth** | ❌ | ✅ (with -ENS) |
| **HTML reports** | ❌ | ✅ |
| **Multi-threading** | ✅ (built-in) | ✅ (-t option) |
| **Whitelist** | Per-file ignores | Global whitelist |
| **Output formats** | Text warnings | Text, XML, HTML, CSV, Checkstyle |

---

## Performance Comparison

**Small Python project (estimated for your codebase):**
- **Ruff C901**: ~50-100ms (part of full ruff check)
- **Lizard Python-only**: ~200-500ms
- **Lizard All languages**: ~500ms-1s

**Practical Impact**: Lizard would add <1 second to pre-commit hooks, negligible for developer workflow.

---

## Recommended Approach for Your Project

### Option 1: Add Lizard for TypeScript, Keep Ruff for Python (Recommended)

**Rationale**:
- Ruff is already configured and extremely fast for Python
- TypeScript needs complexity checking
- Lizard excels at multi-language analysis
- Different tools optimized for their domains

**Configuration**:
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    # Keep existing Ruff for Python (includes C901)
    - id: ruff-check
      name: ruff check
      entry: uv run ruff check --fix
      language: system
      types: [python]

- repo: https://github.com/terryyin/lizard
  rev: 1.20.0
  hooks:
    # Add Lizard for TypeScript/Go
    - id: lizard
      name: lizard typescript complexity
      args: ['--CCN', '15', '-l', 'typescript', 'frontend/']
      types: [ts, tsx]
```

**Pros**:
- Best tool for each language
- No impact on existing Python workflow
- Adds TypeScript coverage
- Ready for future Go code

**Cons**:
- Maintain two complexity tools
- Slightly different reporting formats

---

### Option 2: Replace Ruff C901 with Lizard for Unified Multi-Language

**Rationale**:
- Single tool for all languages
- Unified complexity reporting
- Simpler mental model

**Configuration**:
```yaml
# .pre-commit-config.yaml
- repo: https://github.com/terryyin/lizard
  rev: 1.20.0
  hooks:
    - id: lizard
      name: lizard complexity check
      args: [
        '--CCN', '10',           # Match current Ruff threshold
        '--length', '1000',
        '-l', 'python',
        '-l', 'typescript',
        '-l', 'go',
        '--warnings_only'
      ]
```

**pyproject.toml changes**:
```toml
[tool.ruff.lint]
select = [
    # Remove C901 from list
    "E", "F", "I", "N", "W", "B", "C4", "UP",
    "PLR2004", "PLC0415", "PLR0915",  # Removed C901
    ...
]

# Remove [tool.ruff.lint.mccabe] section
```

**Pros**:
- One complexity tool to rule them all
- Consistent thresholds across languages
- Unified reporting
- Less mental overhead

**Cons**:
- Slower than Ruff for Python
- Need to recalibrate thresholds (Lizard may flag different functions)
- Lose Ruff's integration benefits

---

### Option 3: Keep Both Ruff and Lizard for Redundancy

**Rationale**:
- Cross-validation of Python complexity
- Lizard covers additional languages
- Maximum coverage

**Not Recommended**: Redundant for Python, maintenance burden outweighs benefits.

---

## Current Project Baseline Analysis

Your current Python complexity configuration:
```toml
[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.complexipy]
# (cognitive complexity, different metric)
```

**If you add Lizard for TypeScript**, suggested starting thresholds:
```bash
# Check current TypeScript complexity
lizard -l typescript frontend/ --CCN 15
```

Common TypeScript patterns that may need higher thresholds:
- React component lifecycle methods
- Redux reducers with switch statements
- Form validation logic
- API response handlers

**Recommended initial TypeScript threshold**: CCN 15-20 (React complexity typical)

---

## Implementation Plan

### Phase 1: Add Lizard for TypeScript (No Changes to Python)

1. **Baseline Current TypeScript**:
   ```bash
   pip install lizard
   lizard -l typescript frontend/src/ --csv > typescript-baseline.csv
   ```

2. **Identify Maximum CCN**:
   ```bash
   lizard -l typescript frontend/src/ -s cyclomatic_complexity | head -20
   ```

3. **Add Pre-commit Hook** (set threshold 1 above max):
   ```yaml
   - repo: https://github.com/terryyin/lizard
     rev: 1.20.0
     hooks:
       - id: lizard
         name: lizard typescript
         args: ['--CCN', 'XX', '-l', 'typescript', '--warnings_only']
         types: [ts, tsx]
   ```

4. **Test**:
   ```bash
   pre-commit run lizard --all-files
   ```

### Phase 2: Progressive Threshold Reduction

- Monitor new TypeScript code
- Lower threshold after refactoring complex components
- Target: CCN ≤ 15 for most functions

---

## Key Differences: Cyclomatic vs Cognitive Complexity

**Important Note**: This research focused on cyclomatic complexity (Ruff C901 and Lizard).

Your project **also uses complexipy for cognitive complexity**, which is a different metric:

| Metric | Tool | Focus | Use Case |
|--------|------|-------|----------|
| **Cyclomatic** | Ruff C901, Lizard | Execution paths, test coverage | Testability |
| **Cognitive** | complexipy | Human readability, nesting penalties | Maintainability |

**Recommendation**: Keep both types of metrics:
- **Cyclomatic** (Ruff/Lizard): Ensures testability
- **Cognitive** (complexipy): Ensures maintainability

They measure different aspects of complexity and are complementary.

---

## Conclusion

**For your multi-language project:**

✅ **Recommended**: **Add Lizard for TypeScript, keep Ruff C901 for Python**
- TypeScript needs complexity checking (currently none)
- Ruff is perfect for Python (fast, integrated)
- Lizard is perfect for TypeScript/Go (multi-language)
- Ready for future Go additions

**Command to try Lizard now:**
```bash
# Install
pip install lizard

# Analyze TypeScript
lizard -l typescript frontend/src/

# Analyze everything
lizard -l python services/ -l typescript frontend/
```

The research is documented in [.copilot-tracking/research/20250107-python-complexity-tools-precommit-research.md](.copilot-tracking/research/20250107-python-complexity-tools-precommit-research.md).

## Recommended Approach

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
