<!-- markdownlint-disable-file -->
# Task Research Notes: Pre-commit Standalone Configuration

## Research Executed

### File Analysis
- [.pre-commit-config.yaml](.pre-commit-config.yaml#L1-L216)
  - Uses `repo: local` for 27 out of 28 hooks (96%)
  - Local hooks use `language: system` which relies on tools from current working tree
  - Tools invoked: `uv`, `npm`, `npx`, `python`, `bash`, custom scripts
  - Custom scripts: `scripts/add-copyright`, `scripts/check_commit_duplicates.py`
- [pyproject.toml](pyproject.toml#L1-L234)
  - Tools managed via `uv` dependency groups: `ruff`, `mypy`, `complexipy`, `lizard`, `diff-cover`, `autocopyright`, `pre-commit`, `pytest`
- [frontend/package.json](frontend/package.json#L1-L80)
  - Frontend tools managed via npm: `eslint`, `prettier`, `typescript`, `vitest`
  - `jscpd` is **NOT** in package.json - invoked via `npx --yes` which downloads on demand
- [scripts/add-copyright](scripts/add-copyright)
  - Bash script that runs `uv run autocopyright` with specific arguments
- [scripts/check_commit_duplicates.py](scripts/check_commit_duplicates.py)
  - Python script that processes jscpd output to filter duplicates

### External Research
- #fetch:https://pre-commit.com/#creating-new-hooks
  - Pre-commit supports multiple language types with different dependency management approaches
  - `language: system` - uses system-installed executables, no environment creation
  - `language: python` - creates isolated virtualenv, installs package from repo
  - `language: node` - creates isolated node environment, installs package from repo
  - `additional_dependencies` - allows installing extra packages into isolated environment
  - `repo: local` can use any language that supports `additional_dependencies` or simple languages like `system`

### Project Conventions
- Uses `uv` for Python dependency management with virtual environments
- Uses `npm` for frontend dependency management
- Pre-commit hooks run via `uv tool run pre-commit` or `pre-commit` directly
- Development workflow documented in [README.md](README.md#L142-L184)

## Key Discoveries

### Current Configuration Analysis

**Dependency on Working Tree:**
1. **Python tools via `uv`**: ruff, mypy, complexipy, pytest, diff-cover, autocopyright
   - Invoked via `uv run <tool>` which uses project's pyproject.toml
   - Requires project virtual environment to be set up
2. **Node.js tools via `npm`**: eslint, prettier, typescript, vitest
   - Invoked via `cd frontend && npm run <script>` which uses project's package.json
   - Requires `npm install` to be run in frontend/ directory
3. **npx tools**: jscpd
   - `npx --yes jscpd` downloads tool on first use, caches globally
   - Actually **standalone already** - doesn't depend on working tree
4. **Custom scripts**: `scripts/add-copyright`, `scripts/check_commit_duplicates.py`
   - Bash and Python scripts in the repository
   - Would need to be packaged or moved to eliminate dependency

### Language Type Comparison

| Language | Environment | Caching | Additional Deps | Current Usage |
|----------|------------|---------|-----------------|---------------|
| `system` | None | None | No | All local hooks (27) |
| `python` | Isolated venv | Pre-commit cache | Yes | Not used |
| `node` | Isolated node_env | Pre-commit cache | Yes | Not used |
| `pygrep` | None | None | N/A | Used for 1 hook |

### Pre-commit Language Capabilities

**Languages that can be standalone (from pre-commit docs):**

```python
# From pre-commit source code analysis
languages = {
    'python': python,      # Can install packages, create isolated env
    'node': node,          # Can install packages, create isolated env
    'ruby': ruby,          # Can install packages, create isolated env
    'rust': rust,          # Can install packages, create isolated env
    'golang': golang,      # Can install packages, create isolated env
    'system': unsupported, # Uses system binaries, no isolation
    'pygrep': pygrep,      # Pure regex, no dependencies
    # ... many more
}
```

**Key insight from source:** Languages with `ENVIRONMENT_DIR != None` can install dependencies and create isolated environments that pre-commit manages and caches.

## Recommended Approach: Use Official Hook Repositories + Local Hooks

### Strategy Overview

The best approach is a **two-tier strategy**:

1. **Use official hook repositories** for standard tools (ruff, mypy, prettier, etc.)
   - Cleaner configuration with versioned releases
   - No need to specify `additional_dependencies`
   - Can use `pre-commit autoupdate` for automatic version bumps
   - Already maintained and optimized by tool authors

2. **Use `repo: local`** only for custom logic
   - Custom wrapper scripts (add-copyright, check_commit_duplicates)
   - Project-specific configurations that can't be externalized
   - Tools without official pre-commit repositories

This approach allows pre-commit to:
- Create isolated environments per tool
- Cache environments in `~/.cache/pre-commit`
- Work without requiring `npm install` or `uv sync` in the working tree
- Be portable across machines with just `.pre-commit-config.yaml`

### Implementation Phases

#### Phase 1: Python Tools (Use Official Repositories)

**Current pattern:**
```yaml
- repo: local
  hooks:
    - id: ruff-check
      name: ruff lint
      entry: uv run ruff check --fix
      language: system
      types: [python]
```

**Best practice - use official repository:**
```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.9.0
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format
```

**Alternative - repo: local (only if customization needed):**
```yaml
- repo: local
  hooks:
    - id: ruff-check
      name: ruff lint
      entry: ruff check --fix
      language: python
      types: [python]
      additional_dependencies: ['ruff~=0.9.0']
```

**Tools with official repositories:**
- `ruff` → `https://github.com/astral-sh/ruff-pre-commit`
- `mypy` → `https://github.com/pre-commit/mirrors-mypy`
- `prettier` → `https://github.com/pre-commit/mirrors-prettier`
- `eslint` → `https://github.com/pre-commit/mirrors-eslint`
- `typescript` → `https://github.com/pre-commit/mirrors-typescript`

**Tools requiring `repo: local`:**
- `pytest` with coverage (custom bash wrapper for output filtering)
- `diff-cover` (needs git diff logic)
- `complexipy` (no official repo)
- `lizard` (no official repo)
- Custom scripts (add-copyrigUse Official Repositories)

**Current pattern:**
```yaml
- id: eslint
  name: ESLint
  entry: bash -c 'cd frontend && npm run lint:fix'
  language: system
  files: ^frontend/.*\.(ts|tsx|js|jsx)$
```

**Best practice - use official repository:**
```yaml
- repo: https://github.com/pre-commit/mirrors-prettier
  rev: v3.7.4
  hooks:
    - id: prettier
      files: ^frontend/
      args: [--write, --config, frontend/.prettierrc.json]
```

**Challenge for ESLint/TypeScript:** These tools reference config files in `frontend/` subdirectory. Official repos may not support custom config paths easily.

**Solution options:**

1. **Use official repos with config path args (preferred):**
```yaml
- repo: https://github.com/pre-commit/mirrors-eslint
  rev: v9.0.0
  hooks:
    - id: eslint
      files: ^frontend/
      args: [--config, frontend/eslint.config.js, --fix]
      additional_dependencies:
        - '@typescript-eslint/eslint-plugin@^8.0.0'
        - '@typescript-eslint/parser@^8.0.0'
        # ... other plugins
```

2. **Use `repo: local` with `language: node` (if official repo doesn't support config path):**
```yaml
- repo: local
  hooks:
    - id: eslint
      entry: eslint --config frontend/eslint.config.js
      language: node
      files: ^frontend/.*\.(ts|tsx|js|jsx)$
      additional_dependencies: ['eslint@^9.0.0', ...]
```

3. **Keep as system hooks (fallback):**
   - For complex tools where official repo doesn't fit
   - Document `npm install` requirement

**Recommended approach:**
- `prettier` → Use official repo (simple config path support)
- `eslint` → Try official repo with `additional_dependencies`, fall back to `repo: local` if needed
- `typescript` → Use official repo
- `vitest`, frontend build → Keep as `language: system` (too complex)commit:**
   - Would create redundant package.json just for hooks
   - Maintenance burden - keep two package.json in sync
   - Not recommended

3. **Keep as system hooks but document npm install requirement:**
   - Least invasive
   - Doesn't achieve standalone goal

**Recommended for Node.js tools:** Option 1 with careful config path management

**Tools to migrate:**
- `eslint` - complex, many plugins needed
- `prettier` - straightforward
- `typescript` (tsc) - straightforward
- `vitest` - complex, needs many deps
- Frontend build check - very complex, many deps

#### Phase 3: Special Cases

**jscpd (already standalone via npx):**
```yaml
# Current approach is already optimal
- id: jscpd-diff
  entry: bash -c 'npx --yes jscpd ...'
  language: system
```
Alternative with node language:
```yaml
- id: jscpd-diff
  entry: jscpd services shared frontend/src --config .jscpd.json ...
  language: node
  additional_dependencies: ['jscpd']
```

**Custom scripts requiring migration:**

1. **add-copyright (autocopyright wrapper):**
   - Option A: Inline the logic into pre-commit config
   ```yaml
   - id: add-copyright-python
     entry: autocopyright -s "#" -d services -d shared ...
     language: python
     additional_dependencies: ['autocopyright~=1.1.0']

   - id: add-copyright-typescript
     entry: autocopyright -s "//" -d frontend/src ...
     language: python
     additional_dependencies: ['autocopyright~=1.1.0']
   ```
   - Option B: Create a proper hook repository with `.pre-commit-hooks.yaml`
   - **Recommended:** Option A - simpler, no separate repo needed

2. **check_commit_duplicates.py:**
   - Small Python script that processes jscpd JSON output
   - Option A: Inline into pre-commit config (if simple enough)
   - Option B: Package as installable Python module
   - Option C: Keep as system hook, accept dependency
   - **Recommended:** Option C initially, then Option B if distribution needed

**act (CI testing tool):**
```yamlOptimal Standalone Configuration

```yaml
# Pre-commit configuration optimized for standalone usage
# Uses official repositories where available, repo: local only when needed
default_language_version:
  python: python3.13
  node: "20"

repos:
  # Standard file checks (already standalone)
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: [--unsafe]
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: check-merge-conflict
      - id: detect-private-key

  # Python tools - use official repositories
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0
    hooks:
      - id: mypy
        args: [shared/, services/]
        pass_filenames: false
        additional_dependencies:
          - sqlalchemy[asyncio]~=2.0.36  # For type stubs
          - types-redis
          # Add other type stub packages as needed

  # Node.js tools - use official repositories
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.7.4
    hooks:
      - id: prettier
        files: ^frontend/
        args: [--write, --config, frontend/.prettierrc.json]

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.0.0
    hooks:
      - id: eslint
        files: ^frontend/
        args: [--config, frontend/eslint.config.js, --fix]
        additional_dependencies:
          - '@typescript-eslint/eslint-plugin@^8.0.0'
          - '@typescript-eslint/parser@^8.0.0'
          - 'eslint-plugin-react@^7.37.5'
          - 'eslint-plugin-react-hooks@^7.0.0'
          - 'eslint-plugin-react-refresh@^0.4.25'
          - 'eslint-plugin-prettier@^5.5.4'
          - 'eslint-config-prettier@^10.1.8'
          - '@eslint/js@^9.39.2'
          - 'globals@^16.5.0'

  # Local hooks - custom logic or tools without official repos
  - repo: local
    hooks:
      # Copyright headers - custom wrapper script
      - id: add-copyright-python
        name: Add copyright headers (Python)
        entry: autocopyright -s "#" -d services -d shared -d tests -g "*.py" -l "./templates/agpl-template.jinja2"
        language: python
        files: \.py$
        additional_dependencies: ['autocopyright~=1.1.0']
        pass_filenames: false

      - id: add-copyright-typescript
        name: Add copyright headers (TypeScript)
        entry: autocopyright -s "//" -d frontend/src -g "*.ts" -g "*.tsx" -l "./templates/agpl-template.jinja2"
        language: python
        files: \.(ts|tsx)$
        additional_dependencies: ['autocopyright~=1.1.0']
        pass_filenames: false

      # Python compilation check - uses stdlib
      - id: python-compile
        name: Python compilation check
        entry: python -m compileall -q services shared tests
        language: python
        types: [python]
        pass_filenames: false

      # TypeScript type check - needs custom tsconfig path
      - id: typescript
        name: TypeScript check
        entry: tsc --project frontend/tsconfig.json --noEmit
        language: node
        files: ^frontend/.*\.(ts|tsx)$
        pass_filenames: false
        additional_dependencies: ['typescript@^5.9.3']

      # Complexity tools - no official repos
      - id: complexipy
        name: complexipy cognitive complexity check
        entry: complexipy services shared scripts
        language: python
        types: [python]
        pass_filenames: false
        additional_dependencies: ['complexipy~=4.2.0']

      - id: lizard-typescript
        name: lizard typescript complexity check
        entry: lizard -l typescript frontend/src/ --CCN 15 --warnings_only
        language: python
        files: ^frontend/src/.*\.(ts|tsx)$
        pass_filenames: false
        additional_dependencies: ['lizard~=1.20.0']

      # Test coverage - custom bash logic
      - id: pytest-coverage
        name: Python unit tests with coverage
        entry: bash -c 'pytest --cov --cov-report=xml --cov-report= -qq 2>&1 || exit 1'
        language: python
        pass_filenames: false
        files: ^(services|shared|tests)/.*\.py$
        additional_dependencies:
          - 'pytest~=8.3.0'
          - 'pytest-asyncio~=0.24.0'
          - 'pytest-cov~=6.0.0'
          # Note: Full app dependencies needed for tests to run
          # Consider keeping as system hook if this list gets too long

      - id: diff-coverage
        name: Python diff coverage check
        entry: bash -c 'py_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^(services|shared)/.*\.py$"); if [ -n "$py_files" ]; then diff-cover coverage.xml --compare-branch=origin/main --fail-under=80; fi'
        language: python
        pass_filenames: false
        always_run: true
        additional_dependencies: ['diff-cover~=9.2.0']

      - id: diff-coverage-frontend
        name: Frontend diff coverage check
        entry: bash -c 'ts_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^frontend/src/.*\.(ts|tsx)$"); if [ -n "$ts_files" ]; then diff-cover frontend/coverage/lcov-fixed.info --compare-branch=origin/main --fail-under=80; fi'
        language: python
        pass_filenames: false
        always_run: true
        additional_dependencies: ['diff-cover~=9.2.0']

      # Duplicate detection - custom Python post-processor
      - id: jscpd-diff
        name: Check for duplicates in changed lines
        entry: bash -c 'jscpd services shared frontend/src --config .jscpd.json --threshold 100 --format json --output .jscpd-report && python scripts/check_commit_duplicates.py .jscpd-report/jscpd-report.json'
        language: node
        pass_filenames: false
        types_or: [python, ts, tsx, javascript]
        additional_dependencies: ['jscpd']

      # Full duplicate scan (manual)
      - id: jscpd-full
        name: Full duplicate code check (threshold 2%)
        entry: jscpd services shared frontend/src --config .jscpd.json
        language: node
        pass_filenames: false
        types_or: [python, ts, tsx, javascript]
        stages: [manual]
        additional_dependencies: ['jscpd']

  # System hooks - complex builds requiring project dependencies
  - repo: local
    hooks:
      # Frontend build - needs full npm install in frontend/
      - id: frontend-build
        name: Frontend build check
        entry: bash -c 'cd frontend && npm run build'
        language: system
        files: ^frontend/.*\.(ts|tsx|js|jsx|json|css|scss|html)$
        pass_filenames: false

      # Frontend tests - needs full npm install in frontend/
      - id: vitest-coverage
        name: Frontend unit tests with coverage
        entry: bash -c 'cd frontend && npm run test:coverage -- --run'
        language: system
        pass_filenames: false
        files: ^frontend/src/.*\.(ts|tsx|js|jsx)$

      # Act - requires Docker daemon
      - id: ci-cd-workflow
        name: Run CI/CD workflow locally
        entry: act -j unit-tests --rm
        language: system
        pass_filenames: false
        always_run: true
        stages: [manual]

      # Manual test hooks (require project setup)
      - id: pytest-all
        name: pytest all unit tests
        entry: uv run pytest tests/services/ tests/shared/ --tb=short
        language: system
        pass_filenames: false
        stages: [manual]

      - id: vitest-all
        name: All frontend unit tests
        entry: bash -c 'cd frontend && npm run test'
        language: system
        pass_filenames: false
        stages: [manual]
```

### When to Use `repo: local` vs Official Repositories

**Use official repository when:**
- ✅ Tool has an official pre-commit repo (check https://pre-commit.com/hooks.html)
- ✅ Default configuration works for your project
- ✅ You want automatic version updates via `pre-commit autoupdate`

**Use `repo: local` when:**
- ⚙️ You have custom wrapper scripts or logic
- ⚙️ Replace tools with official repositories first:**
   ```bash
   # Update .pre-commit-config.yaml to use official repos
   # For example, replace local ruff with:
   # - repo: https://github.com/astral-sh/ruff-pre-commit

   # Install new hooks
   pre-commit install --install-hooks

   # Test official repo hooks
   pre-commit run ruff --all-files
   pre-commit run prettier --all-files
   ```

2. **Convert custom tools to `repo: local` with proper language:**
   ```bash
   # Test individual conversions
   pre-commit run complexipy --all-files
   pre-commit run typescript --all-files
   ```

3. **Verify isolated environments created:**
   ```bash
   ls ~/.cache/pre-commit/
   # Should see directories like:
   #   github.com-astral-sh-ruff-pre-commit-xxx
   #   repoxxx-py_env-python3.13 (for local hooks)
   ```

4. **Test autoupdate functionality:**
   ```bash
   # Official repos can be auto-updated
   pre-commit autoupdate
   # This updates all official repositories to latest versions
   ```

5. **Document remaining system dependencies:**
   - Some hooks (frontend build, vitest, act) remain as `system`
   - Update README with: "Most hooks are standalone, but frontend tests/build require `cd frontend && npm install`"
- Node.js 20+ available in PATH (for Node-based hooks)
- Docker (only for act hook, which is manual stage)

### Migration Steps

1. **Test individual tool migrations:**
   ```bash
   # Test one Python tool first
   pre-commit run ruff-check --all-files

   # Test one Node tool
   pre-commit run prettier --all-files
   ```

2. **Verify isolated environments created:**
   ```bash
   ls ~/.cache/pre-commit/
   # Should see directories like: repoxxx-py_env-python3.13
   ```

3. **Remove old hook invocations:**
   - After confirming standalone hooks work, remove `uv` and `npm run` wrappers
   - Hooks will be faster (no overhead of wrapper scripts)

4. **Document remaining system dependencies:**
   - Some hooks (frontend build, vitest, act) may remain as `system` if dependencies are too extensive
   - Document that users need `npm install` in frontend/ for those hooks

### Trade-offs

**Use official repositories:** (highest priority)
- ✅ ruff → `https://github.com/astral-sh/ruff-pre-commit`
- ✅ mypy → `https://github.com/pre-commit/mirrors-mypy`
- ✅ prettier → `https://github.com/pre-commit/mirrors-prettier`
- ✅ eslint → `https://github.com/pre-commit/mirrors-eslint`

**Use `repo: local` with proper language:** (when no official repo)
- ⚙️ complexipy (python)
- ⚙️ lizard (python)
- ⚙️ typescript (node) - needs custom config path
- ⚙️ autocopyright wrapper (python)
- ⚙️ jscpd + duplicate checker (node + custom script)

**Keep as `language: system`:** (requires project environment)
- 🔧 pytest with coverage (needs all app dependencies)
- 🔧 vitest with coverage (needs all frontend dependencies)
- 🔧 frontend build (needs full npm toolchain)
- 🔧 act (needs Docker daemon)
- 🔧 diff-coverage (could convert but adds complexity)

**Document requirements:**
```markdown
## Pre-commit Setup

### Quick Start (Works Immediately)
Most hooks are standalone using official repositories:
```bash
pre-commit install
pre-commit run --all-files  # Works without npm install or uv sync!
```

### Tools Requiring Project Setup
A few hooks need project dependencies installed:
- **Python tests** (pytest-coverage): Run `uv sync` first
- **Frontend tests/build** (vitest-coverage, frontend-build): Run `cd frontend && npm install` first
- **CI testing** (ci-cd-workflow): Install Docker and act

These system hooks are marked as such in the config and won't fail if dependencies are missing.
- act (needs Docker)

**Document requirements:**
```markdown
## Pre-commit Setup

### Automatic Tools
Most hMost tools use official repositories (`github.com/pre-commit/` or `github.com/astral-sh/`)
- [ ] Can run `pre-commit autoupdate` to bump versions automatically
- [ ] `repo: local` only used for custom logic or tools without official repos
- [ ] Can clone repo and run `pre-commit run --all-files` without errors (except documented system hooks)
- [ ] Linting/formatting hooks (ruff, prettier, eslint) work without `uv sync` or `npm install`
- [ ] Complex hooks (tests, builds) clearly documented as requiring project setup
- [ ] Configuration is maintainable and follows pre-commit best practices
- [ ] Hook execution time similar or faster than current setup
- [ ] Clear distinction between standalone hooks and system-dependent hooks
### Tools Requiring Additional Setup
Some hooks need project dependencies:
- Python tests: Run `uv sync` to install test dependencies
- Frontend tests/build: Run `cd frontend && npm install`
- CI workflow testing: Install Docker and act
```

### Success Criteria

- [ ] Can clone repo and run `pre-commit run --all-files` without errors (except system hooks)
- [ ] Simple hooks (ruff, prettier, typescript) work without `uv sync` or `npm install`
- [ ] Complex hooks (tests, builds) documented as requiring project setup
- [ ] Configuration is maintainable (not excessively long or complex)
- [ ] Hook execution time similar or faster than current setup
