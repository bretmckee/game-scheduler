<!-- markdownlint-disable-file -->
# Task Research Notes: Coverage Collection for Unit, Integration, and E2E Tests Analysis

## Research Executed

### External Research
- #fetch:https://docs.astral.sh/ruff/rules/
  - Comprehensive catalog of 800+ available Ruff rules
  - Rule categories, stability status, and auto-fix capabilities
  - Documentation for security, async, FastAPI, performance, and code quality rules

### Current Configuration Analysis
- File: pyproject.toml
  - Current selection: `["E", "F", "I", "N", "W", "B", "C4", "UP", "PLR2004", "PLC0415", "C901", "PLR0915"]`
  - Primarily using pycodestyle (E/W), Pyflakes (F), isort (I), pep8-naming (N), bugbear (B), comprehensions (C4), pyupgrade (UP), and selective Pylint rules
  - Preview mode enabled, targeting Python 3.13

### Empirical Testing
- Command: `ruff check --select S,ASYNC,FAST --exclude tests --statistics`
  - Security (S): 92 issues in production code (vs 3,336 including tests)
  - Async (ASYNC): Minimal issues, mostly covered
  - FastAPI (FAST): 77 dependency annotation issues

- Command: `ruff check --select TC,RET,SIM,PERF,PLE,PLW,PLC --exclude tests --statistics`
  - Type checking (TC): 9 issues (all auto-fixable)
  - Return statements (RET): 15 issues (mostly auto-fixable)
  - Simplify (SIM): 5 issues
  - Performance (PERF): 1 issue
  - Pylint (PLE/PLW/PLC): 20 issues

- Command: `ruff check --select EM,ARG,G,LOG,RUF --exclude tests --statistics`
  - Logging (G/LOG): 368 issues (335 f-strings in logging)
  - Error messages (EM): 77 issues (all auto-fixable)
  - Unused arguments (ARG): 27 issues
  - Ruff-specific (RUF): 71 issues (many auto-fixable)

## Key Discoveries

### Current Rule Coverage
**Strengths:**
- Good foundational coverage with pycodestyle, Pyflakes, and bugbear
- Modern Python practices via pyupgrade
- Import organization via isort
- Code complexity controls (C901, PLR0915)

**Gaps:**
- No security scanning (S/bandit)
- No async/await best practices (ASYNC)
- No FastAPI-specific checks (FAST)
- Limited Pylint rule coverage
- No performance checks (PERF)
- No logging best practices (G/LOG)
- Missing type-checking import optimization (TC)

### Issue Statistics (Production Code Only)

**Total: 878 issues across new rule categories** (686 original + 97 T20 + 4 ERA + 94 ANN + 0 A/DTZ/ICN/PT)

#### High Priority - Security & Correctness (92 issues)
```
77    FAST002  FastAPI non-annotated dependency
2     S608     Hardcoded SQL expression (SECURITY CRITICAL)
4     S603/607 Subprocess security issues
3     S101     Assert in production code
6     S104/107/108/110/404  Other security issues
```

#### Medium Priority - Code Quality (51 issues)
```
15    PLW0603  Global statement usage
15    RET504/502/505/506  Return statement improvements [AUTO-FIXABLE]
9     TC001/002/003/005  Type-checking imports [AUTO-FIXABLE]
5     SIM105/102  Code simplifications
4     PLC2701  Import from private modules
3     Other improvements
```

#### Lower Priority - Polish & Performance (543 issues)
```
335   G004     F-strings in logging (performance concern)
77    EM101/102  Exception message extraction [AUTO-FIXABLE]
36    RUF100   Unused noqa comments [AUTO-FIXABLE]
31    G201     Logging .error() should be .exception()
27    ARG001/002/004  Unused function arguments
10    RUF029   Unnecessary async functions
27    Other misc improvements [MOSTLY AUTO-FIXABLE]
```

### Critical Findings

**Immediate Security Concerns:**
1. **S608**: 2 instances of hardcoded SQL expressions - potential SQL injection
2. **S603/S607**: 4 subprocess security issues requiring review
3. **S101**: 3 asserts in production code (disabled in optimized Python)

**Performance Issues:**
- 335 f-strings in logging statements cause unnecessary string interpolation even when log level is disabled
- Pattern: `logger.info(f"Message {variable}")` should be `logger.info("Message %s", variable)`

**Code Quality Opportunities:**
- 77 FastAPI dependencies lacking proper `Annotated` type hints
- 15 global statement usages that could indicate architectural issues
- 10 functions marked async but never using await

**Auto-Fixable Low-Hanging Fruit:**
- 137 issues can be automatically fixed (return statements, exception messages, noqa comments, type imports)

## Recommended Approach

### Phase 1: Critical Security & Correctness (Weeks 1-2)
**Objective:** Address security vulnerabilities and correctness issues

**Rules to Enable:**
```toml
select = [
    # ... existing rules ...
    "S",      # flake8-bandit security checks
    "ASYNC",  # flake8-async
    "FAST",   # FastAPI-specific
]

ignore = [
    "S101",   # Allow assert (will ignore in tests anyway)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",   # Assert usage
    "S106",   # Hardcoded passwords in fixtures
    "S105",   # Hardcoded password strings
]
```

**Implementation Process:**
1. Fix all S, ASYNC, FAST violations (92 issues in production code)
2. Verify zero violations: `ruff check --select S,ASYNC,FAST --exclude tests`
3. Add rules to pyproject.toml
4. Commit configuration change
5. Rules now enforced in CI/CD with zero violations

**Actions:**
1. **IMMEDIATE**: Review and fix 2 S608 SQL injection warnings
2. Review 4 subprocess security issues (S603/S607)
3. Fix 3 production asserts (S101)
4. Address 77 FastAPI `Annotated` dependency issues
5. Review remaining security warnings

**Success Criteria:**
- Zero S608 SQL injection warnings
- All subprocess calls reviewed and documented
- No asserts in production code paths
- All FastAPI routes use proper `Annotated` dependencies

### Phase 2: Code Quality & Maintainability (Weeks 3-4)
**Objective:** Improve code structure and readability

**Rules to Add:**
```toml
select = [
    # ... Phase 1 rules ...
    "RET",    # flake8-return
    "SIM",    # flake8-simplify
    "TC",     # flake8-type-checking
    "PLE",    # Pylint errors
    "PLW",    # Pylint warnings
    "PLC",    # Pylint conventions
    "T20",    # flake8-print
    "ERA",    # eradicate (commented-out code)
    "A",      # flake8-builtins
    "DTZ",    # flake8-datetimez
    "ICN",    # flake8-import-conventions
    "PT",     # flake8-pytest-style
]
```

**Implementation Process:**
1. Fix all violations (152 issues: 51 existing + 97 T20 + 4 ERA)
2. Verify zero violations: `ruff check --select RET,SIM,TC,PLE,PLW,PLC,T20,ERA,A,DTZ,ICN,PT --exclude tests`
3. Add rules to pyproject.toml
4. Commit configuration change
5. Rules now enforced in CI/CD with zero violations

**Actions:****
1. Auto-fix 15 return statement improvements (RET504/502/505/506)
2. Auto-fix 9 TYPE_CHECKING imports (TC001/002/003/005)
3. Review and address 15 global statement usages (PLW0603)
4. Implement 5 code simplifications (SIM105/102)
5. Review 4 private module imports (PLC2701)6. **Replace 97 print statements with logging (T201)**
7. **Remove 4 commented-out code blocks (ERA001)**
8. **Enable A, DTZ, ICN, PT rules (0 violations, enforce going forward)**
**Success Criteria:**
- All auto-fixable issues resolved
- Global usage documented or refactored
- Code complexity reduced through simplifications

### Phase 3: Logging Performance Optimization (Weeks 5-6)
**Objective:** Fix f-strings in logging statements for performance

**Rules to Add:**
```toml
select = [
    # ... Phase 1 & 2 rules ...
    "G004",   # logging-f-string specifically
]
```

**Implementation Process:**
1. Fix all G004 violations (335 f-strings in logging)
2. Verify zero violations: `ruff check --select G004 --exclude tests`
3. Add G004 to pyproject.toml select list
4. Commit configuration change
5. Rule now enforced in CI/CD with zero violations

**Actions:**
1. **Major**: Fix 335 f-strings in logging (G004) - significant performance impact
2. Convert logger.info(f"Message {var}") to logger.info("Message %s", var)
3. Validate logging still works correctly in all contexts

**Success Criteria:**
- Zero f-strings in logging
- All logging uses lazy formatting
- Performance improvement measurable

### Phase 4: Polish & Cleanup (Weeks 7-8)
**Objective:** Clean up code style and remaining performance issues

**Rules to Add:**
```toml
select = [
    # ... Phase 1, 2, 3 rules ...
    "PERF",   # Perflint performance
    "G",      # flake8-logging-format (rest of G rules)
    "LOG",    # flake8-logging
    "EM",     # flake8-errmsg
    "RUF",    # Ruff-specific rules
]
```

**Implementation Process:**
1. Fix all PERF, G (except G004), LOG, EM, RUF violations (208 issues)
2. Verify zero violations: `ruff check --select PERF,G,LOG,EM,RUF --exclude tests`
3. Add rules to pyproject.toml
4. Commit configuration change
5. Rules now enforced in CI/CD with zero violations

**Actions:**
1. Fix 31 logging .error() to .exception() (G201)
2. Auto-fix 77 exception message extractions (EM101/102)
3. Auto-fix 36 unused noqa comments (RUF100)
4. Review 10 unnecessary async functions (RUF029)
5. Fix remaining logging and performance issues

**Success Criteria:**
- All logging .error() converted to .exception() where appropriate
- Exception messages properly extracted
- No unused noqa comments
- Async only where needed
- All performance optimizations applied

### Phase 5: Type Annotations (Weeks 9-10)
**Objective:** Add comprehensive type hints throughout codebase

**Rules to Add:**
```toml
select = [
    # ... all previous rules ...
    "ANN",    # flake8-annotations
]

ignore = [
    "S101",     # Allow assert (tests handle separately)
    "ANN101",   # Missing type annotation for self (deprecated)
    "ANN102",   # Missing type annotation for cls (deprecated)
]
```

**Implementation Process:**
1. Fix all ANN violations (94 type hints)
2. Verify zero violations: `ruff check --select ANN --exclude tests`
3. Add ANN to pyproject.toml
4. Commit configuration change
5. Rule now enforced in CI/CD with zero violations

**Actions:**
1. Add 26 function argument type hints (ANN001)
2. Add 27 special method return types (ANN204)
3. Add 11 public function return types (ANN201)
4. Add 10 private function return types (ANN202)
5. Add 10 **kwargs type hints (ANN003)
6. Add 3 *args type hints (ANN002)
7. Review 3 Any type usages (ANN401)

**Success Criteria:**
- All functions have type hints
- Return types explicitly declared
- Type checker (mypy) benefits from improved hints

### Phase 6: Unused Code Cleanup (Week 11)
**Objective:** Remove dead code and unused parameters

**Rules to Add:**
```toml
select = [
    # ... all previous rules ...
    "ARG",    # flake8-unused-arguments
]
```

**Implementation Process:**
1. Fix all ARG violations (27 unused arguments)
2. Verify zero violations: `ruff check --select ARG --exclude tests`
3. Add ARG to pyproject.toml
4. Commit configuration change
5. Rule now enforced in CI/CD with zero violations

**Actions:**
1. Review 27 unused function/method arguments
2. Either remove, use, or prefix with underscore
3. Document intentionally unused parameters

**Success Criteria:**
- All function signatures reflect actual usage
- Intentional unused parameters documented

## Implementation Guidance

### Testing Strategy
1. **Per-Phase Testing**: After each phase, run full test suite
2. **Incremental Commits**: Commit rule additions separately from fixes
3. **CI/CD Updates**: Update pre-commit hooks and GitHub Actions after each phase

### Configuration Management
**Recommended Final Configuration:**
```toml
[tool.ruff.lint]
select = [
    "E", "F", "I", "N", "W",           # Original rules
    "B", "C4", "UP",                    # Original rules
    "C901", "PLR2004", "PLC0415", "PLR0915",  # Original specific rules
    "S", "ASYNC", "FAST",               # Phase 1: Security
    "RET", "SIM", "TC",                 # Phase 2: Code quality
    "PLE", "PLW", "PLC",                # Phase 2: Pylint
    "PERF", "G", "LOG", "EM", "RUF",   # Phase 3: Performance
    "ARG",                              # Phase 4: Cleanup
]

ignore = [
    "S101",     # Allow assert (tests handle separately)
    "EM101",    # Optional: Can be noisy
    "EM102",    # Optional: Can be noisy
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "PLR2004",  # Magic values (existing)
    "S101",     # Assert usage
    "S106",     # Hardcoded passwords in fixtures
    "S105",     # Hardcoded password strings
    "ARG001",   # Unused function args in fixtures
    "ARG002",   # Unused method args in fixtures
]
```

### Risk Mitigation
**Low Risk (Auto-fixable):**
- Run `ruff check --fix` for EM, RUF100, RET, TC rules
- Review diffs before committing

**Medium Risk (Manual review needed):**
- Security issues (S608, S603, S607)
- Global statements (PLW0603)
- Logging f-strings (G004) - requires code changes

**High Risk (Architectural changes):**
- FastAPI annotations (FAST002) - API contract changes
- Unused async (RUF029) - may affect behavior
- Private imports (PLC2701) - may indicate design issues

### Monitoring & Validation
1. **Pre-commit Hooks**: Update `.pre-commit-config.yaml` with new rules
2. **CI/CD**: Ensure GitHub Actions run with updated configuration
3. **Coverage**: Track rule violation counts over time
4. **Documentation**: Update project documentation with new standards

### Dependencies
- Ruff version: >=0.8.0 (already specified in pyproject.toml)
- No additional dependencies required

## Technical Requirements

### Environment
- Python 3.13 target (already configured)
- Ruff preview mode enabled (already configured)
- Line length: 100 (already configured)

### Excluded Paths (already configured)
- tests/** (except for test-specific rules)
- frontend/**
- docker/**
- alembic/**
- templates/**
- history/**
- scripts/**

### Integration Points
1. **Pre-commit hooks**: Ensure ruff runs with new rules
2. **CI/CD pipeline**: Update GitHub Actions workflows
3. **IDE integration**: VS Code/PyCharm settings may need updates
4. **Developer onboarding**: Update contribution guidelines

## Success Metrics

### Phase 1 (Security)
- Zero critical security warnings (S608)
- All FAST002 issues resolved
- Clean security audit

### Phase 2 (Quality)
- 90%+ auto-fixable issues resolved
- Zero unreviewed global statements
- All type imports optimized

### Phase 3 (Logging Performance)
- Zero f-strings in logging (G004)
- All logging uses lazy formatting

### Phase 4 (Polish & Cleanup)
- Exception messages properly extracted
- Zero unused noqa comments
- All logging patterns correct
- Clean linting output

### Phase 5 (Unused Arguments)
- All function signatures match usage
- No unused parameters

### Overall Success
- **Target**: Zero violations for each rule category before enabling in CI/CD
- **Approach**: Incremental - fix violations, enable rules, commit, repeat
- **Timeline**: 11 weeks for full implementation
- **Quality**: Each phase achieves zero violations before rules are enabled
- **CI/CD**: Each commit after rule enablement maintains zero violations

## References

- [Ruff Rules Documentation](https://docs.astral.sh/ruff/rules/)
- [Blog Post: Ruff Rules Deep Dive](https://jsstevenson.github.io/blog/2024/ruff-rules/)
- Project: `.github/instructions/python.instructions.md`
- Project: `pyproject.toml` current configuration
- Current test coverage: `pytest --cov` baseline established
