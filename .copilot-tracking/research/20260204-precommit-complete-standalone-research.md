<!-- markdownlint-disable-file -->
# Task Research Notes: Pre-commit Complete Standalone Configuration

## Research Executed

### Current Configuration Analysis
- [.pre-commit-config.yaml](.pre-commit-config.yaml#L1-L273)
  - 28 total hooks across all repositories
  - 3 using official repositories (already standalone)
  - 5 using `repo: local` with proper `language: python` or `language: node`
  - **12 hooks still using `language: system`** with `uv run` or `npm run` commands
  - 3 manual hooks also using `language: system`

### System Dependencies Identified

**Hooks using `uv run` (Python dependencies):**
1. `python-compile` - Line 120: `uv run python -m compileall`
2. `mypy` - Line 129: `uv run mypy`
3. `pytest-coverage` - Line 138: `uv run pytest`
4. `diff-coverage` - Line 147: `uv run diff-cover`
5. `diff-coverage-frontend` - Line 185: `uv run diff-cover`
6. `pytest-all` (manual) - Line 249: `uv run pytest`

**Hooks using `npm run` (Node.js dependencies):**
1. `eslint` - Line 108: `cd frontend && npm run lint:fix`
2. `frontend-build` - Line 159: `cd frontend && npm run build`
3. `typescript` - Line 168: `cd frontend && npm run type-check`
4. `vitest-coverage` - Line 176: `cd frontend && npm run test:coverage`
5. `vitest-all` (manual) - Line 258: `cd frontend && npm run test`

**Other system hooks:**
1. `ci-cd-workflow` (manual) - Line 267: `act` (requires Docker)

### External Research
- #fetch:https://pre-commit.com/#supported-languages
  - `language: python` creates isolated virtualenv, installs from `pip install .`
  - `language: node` creates isolated node environment, installs from `npm install .`
  - Both support `additional_dependencies` for adding extra packages
  - `language: system` uses system executables with NO isolation
  - Tools should use `entry` as the command WITHOUT wrapper scripts

### Project Dependencies Analysis
- [pyproject.toml](pyproject.toml#L50-L63)
  - Main dependencies in `[project.dependencies]` include pytest, pytest-asyncio, pytest-cov
  - Dev dependencies in `[project.optional-dependencies]` include mypy, diff-cover
- [frontend/package.json](frontend/package.json#L10-L22)
  - Scripts defined: `build`, `type-check`, `lint:fix`, `test:coverage`
  - DevDependencies include eslint, typescript, vite, vitest with ~50 total packages

## Key Discoveries

### Conversion Strategy by Hook Type

#### Python Tools - Convert to `language: python`

**Simple conversions (no complex dependencies):**

1. **python-compile**: Can use Python stdlib
```yaml
- id: python-compile
  name: Python compilation check
  entry: python -m compileall -q services shared tests
  language: python
  types: [python]
  pass_filenames: false
```

2. **mypy**: Needs type stubs as `additional_dependencies`
```yaml
- id: mypy
  name: mypy type check
  entry: mypy shared/ services/
  language: python
  types: [python]
  pass_filenames: false
  additional_dependencies:
    - 'mypy>=1.10.0'
    - 'sqlalchemy[asyncio]~=2.0.36'
    - 'types-redis'
    - 'types-aiofiles'
    # ... other type stubs
```

3. **diff-cover**: Simple tool with minimal deps
```yaml
- id: diff-coverage
  name: Python diff coverage check
  entry: bash -c 'py_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^(services|shared)/.*\.py$"); if [ -n "$py_files" ]; then diff-cover coverage.xml --compare-branch=origin/main --fail-under=80 --ignore-whitespace; fi'
  language: python
  pass_filenames: false
  always_run: true
  additional_dependencies: ['diff-cover~=9.2.0']
```

**Complex conversions (many dependencies - keep as `language: system`):**

4. **pytest-coverage**: Requires ALL application dependencies
   - Needs: sqlalchemy, fastapi, discord.py, redis, pika, httpx, etc. (40+ packages)
   - Would need to list entire dependency tree in `additional_dependencies`
   - **Recommendation: Keep as `language: system`**, document requirement

#### Node.js Tools - Convert to `language: node`

**Simple conversions:**

1. **prettier**: Already converted ✅

**Moderate conversions (config complexity):**

2. **typescript**: Needs config file path
```yaml
- id: typescript
  name: TypeScript check
  entry: tsc --project frontend/tsconfig.json --noEmit
  language: node
  files: ^frontend/.*\.(ts|tsx)$
  pass_filenames: false
  additional_dependencies: ['typescript@^5.9.3']
```

3. **eslint**: Complex - imports from node_modules
   - eslint.config.js imports ~10 plugins from node_modules
   - Would need ALL plugins in `additional_dependencies`
```yaml
- id: eslint
  name: ESLint
  entry: eslint --config frontend/eslint.config.js --fix
  language: node
  files: ^frontend/.*\.(ts|tsx|js|jsx)$
  pass_filenames: false
  additional_dependencies:
    - 'eslint@^9.39.2'
    - '@typescript-eslint/eslint-plugin@^8.0.0'
    - '@typescript-eslint/parser@^8.0.0'
    - 'eslint-plugin-react@^7.37.5'
    - 'eslint-plugin-react-hooks@^7.0.0'
    - 'eslint-plugin-react-refresh@^0.4.25'
    - 'eslint-plugin-prettier@^5.5.4'
    - 'eslint-config-prettier@^10.1.8'
    - '@eslint/js@^9.39.2'
    - 'globals@^16.5.0'
```

**Complex conversions (many dependencies - keep as `language: system`):**

4. **frontend-build**: Uses vite with 50+ dependencies
   - Would need entire devDependencies from package.json
   - **Recommendation: Keep as `language: system`**, document requirement

5. **vitest-coverage**: Similar to pytest, needs all test dependencies
   - Would need vitest + all its plugins + testing-library packages
   - **Recommendation: Keep as `language: system`**, document requirement

### Critical Issue: Config File Paths

Many tools need to reference config files in subdirectories:
- `frontend/tsconfig.json`
- `frontend/eslint.config.js`
- `frontend/.prettierrc`

When using `language: node` or `language: python`, pre-commit runs hooks from isolated environments. The `entry` command still runs from the repository root, so relative paths work correctly:
- ✅ `tsc --project frontend/tsconfig.json` works
- ✅ `eslint --config frontend/eslint.config.js` works

## Recommended Approach: Tiered Strategy

### Tier 1: Simple Tools - Convert to Proper Language
Convert tools with minimal dependencies that don't need full project context:

**Python:**
- ✅ python-compile → `language: python`
- ✅ mypy → `language: python` with type stubs
- ✅ diff-cover → `language: python`

**Node.js:**
- ✅ typescript → `language: node`
- ⚠️ eslint → `language: node` (requires listing all plugins)

### Tier 2: Complex Tools - Keep as System
Keep tools that need full project dependencies:

**Python:**
- 🔧 pytest-coverage → `language: system` (needs 40+ app dependencies)

**Node.js:**
- 🔧 frontend-build → `language: system` (needs entire vite toolchain)
- 🔧 vitest-coverage → `language: system` (needs test framework + deps)

**Other:**
- 🔧 ci-cd-workflow → `language: system` (needs Docker daemon)

### Tier 3: Document Requirements
Update documentation to clearly state:
- Most hooks run standalone with NO project setup
- A few hooks require project dependencies:
  - Python tests: Run `uv sync` first
  - Frontend tests/build: Run `cd frontend && npm install` first

## Implementation Guidance

### Phase 1: Convert Simple Python Tools
1. Remove `uv run` prefix from entry
2. Change `language: system` → `language: python`
3. Add `additional_dependencies` list
4. Test with: `pre-commit run <hook-id> --all-files`

### Phase 2: Convert Node.js Tools
1. Remove `cd frontend && npm run` wrapper
2. Change to direct command: `tsc --project frontend/tsconfig.json`
3. Change `language: system` → `language: node`
4. Add `additional_dependencies` list
5. Test with config file path resolution

### Phase 3: Document System Hooks
Create clear documentation showing:
- Which hooks require no setup (linters, formatters, type checkers)
- Which hooks require project setup (tests, builds)
- How to install dependencies for system hooks

## Success Criteria

- [ ] Can run `pre-commit install` in fresh clone without errors
- [ ] Linting/formatting hooks (ruff, prettier, eslint, mypy) work without `uv sync` or `npm install`
- [ ] Type checking (mypy, typescript) works standalone
- [ ] Complexity tools (complexipy, lizard) work standalone (already done)
- [ ] Test/build hooks clearly documented as requiring project setup
- [ ] Configuration maintainable - not excessively long dependency lists
- [ ] Hook execution time similar or better than current setup
