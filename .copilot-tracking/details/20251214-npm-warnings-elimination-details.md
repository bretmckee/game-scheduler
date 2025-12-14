<!-- markdownlint-disable-file -->

# Task Details: NPM Warnings Elimination Phase 1

## Research Reference

**Source Research**: #file:../research/20251214-npm-warnings-elimination-research.md

## Phase 1: Vite Upgrade

### Task 1.1: Update Vite 5→6 in package.json

Update Vite dependency from 5.4.21 to ^6.0.0 to resolve esbuild CORS vulnerability.

- **Files**:
  - `frontend/package.json` - Update "vite" version in devDependencies
- **Success**:
  - package.json contains `"vite": "^6.0.0"`
  - No syntax errors in package.json
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 89-96) - Vite upgrade priority and impact
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 166-172) - Phase 1 Vite upgrade steps
- **Dependencies**:
  - None (first task in sequence)

### Task 1.2: Install dependencies and verify esbuild version

Run npm install to update Vite and verify esbuild is upgraded to ≥0.25.0.

- **Files**:
  - `frontend/package-lock.json` - Updated by npm install
  - `frontend/node_modules/` - Updated by npm install
- **Success**:
  - `npm list esbuild` shows esbuild@0.25.0 or higher
  - No installation errors
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 75-90) - esbuild vulnerability details and fix
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Test Vite functionality

Verify Vite dev server, build, and preview work correctly after upgrade.

- **Files**:
  - `frontend/vite.config.ts` - Should work without changes
  - `frontend/dist/` - Build output directory
- **Success**:
  - `npm run dev` starts without errors
  - `npm run build` completes successfully
  - `npm run preview` serves built files
  - No new console warnings or errors
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 169-172) - Vite testing steps
- **Dependencies**:
  - Task 1.2 completion

## Phase 2: ESLint Migration

### Task 2.1: Install ESLint 9 and TypeScript ESLint v8

Update ESLint to version 9 and TypeScript ESLint packages to v8 for compatibility.

- **Files**:
  - `frontend/package.json` - Update eslint, @typescript-eslint/parser, @typescript-eslint/eslint-plugin
- **Success**:
  - package.json contains `"eslint": "^9.0.0"`
  - package.json contains `"@typescript-eslint/parser": "^8.0.0"`
  - package.json contains `"@typescript-eslint/eslint-plugin": "^8.0.0"`
  - npm install completes without errors
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 115-122) - ESLint 9 migration requirements
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 173-179) - ESLint migration steps
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Convert .eslintrc.js to eslint.config.js (flat config)

Migrate ESLint configuration from legacy format to ESLint 9 flat config format.

- **Files**:
  - `frontend/.eslintrc.js` - Delete after migration
  - `frontend/eslint.config.js` - Create new flat config file
- **Success**:
  - `eslint.config.js` exists with valid flat config syntax
  - `.eslintrc.js` removed
  - All existing rules preserved in new format
  - TypeScript parser and plugin configured correctly
  - React plugin configured correctly
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 115-122) - ESLint 9 breaking changes
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 175-176) - Config conversion requirement
  - #fetch:"https://eslint.org/docs/latest/use/migrate-to-9.0.0" - Official ESLint 9 migration guide
- **Implementation Guidance**:
  - Use `@eslint/js` for recommended rules
  - Import TypeScript ESLint config as flat config
  - Import React plugin as flat config
  - Convert `extends` to explicit imports
  - Convert `env` to `languageOptions.globals`
  - Preserve all custom rules from .eslintrc.js
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update ESLint plugins to ESLint 9 compatible versions

Update all ESLint plugins to versions compatible with ESLint 9.

- **Files**:
  - `frontend/package.json` - Update eslint-plugin-react-refresh
- **Success**:
  - All ESLint plugins compatible with ESLint 9
  - npm install completes without peer dependency warnings
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 180-181) - Plugin updates requirement
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Test ESLint across codebase

Run ESLint on entire frontend codebase to verify configuration works correctly.

- **Files**:
  - All TypeScript/TSX files in frontend/src/
- **Success**:
  - `npm run lint` completes without configuration errors
  - No new linting errors introduced (only pre-existing issues allowed)
  - ESLint correctly identifies TypeScript and React syntax
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 182) - Linting test requirement
- **Dependencies**:
  - Task 2.3 completion

## Phase 3: Supporting Packages

### Task 3.1: Update minor version packages

Update Prettier, Vitest, jsdom, and other supporting packages to latest versions.

- **Files**:
  - `frontend/package.json` - Update prettier, vitest, jsdom, eslint-plugin-react-refresh
- **Success**:
  - package.json contains `"prettier": "^3.7.4"`
  - package.json contains `"vitest": "^4.0.15"`
  - package.json contains `"jsdom": "^27.3.0"`
  - package.json contains `"eslint-plugin-react-refresh": "^0.4.25"`
  - npm install completes without errors
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 183-187) - Supporting package updates
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Verify no new deprecation warnings

Run npm install and verify all targeted deprecation warnings are eliminated.

- **Files**:
  - None (verification task)
- **Success**:
  - `npm ci` or `npm install` output shows zero deprecation warnings for:
    - inflight
    - @humanwhocodes/config-array
    - @humanwhocodes/object-schema
    - rimraf
    - glob
    - eslint@8
  - No new deprecation warnings introduced
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 40-75) - Deprecated packages list
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Testing & Validation

### Task 4.1: Run full frontend test suite

Execute all frontend unit and component tests to ensure no regressions.

- **Files**:
  - All test files in frontend/src/
- **Success**:
  - `npm test` passes all tests
  - No new test failures
  - Test coverage maintained
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 188) - Test suite requirement
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Verify Docker builds

Build frontend Docker image to ensure production builds work correctly.

- **Files**:
  - `docker/frontend.Dockerfile`
  - `compose.yaml`
- **Success**:
  - `docker compose build frontend` completes successfully
  - No build errors or warnings
  - Image size remains reasonable
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 189) - Docker build requirement
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Test CI/CD pipeline

Push changes to feature branch and verify GitHub Actions workflow passes.

- **Files**:
  - `.github/workflows/*.yml` - CI/CD configuration
- **Success**:
  - All CI checks pass
  - Linting step succeeds
  - Test step succeeds
  - Build step succeeds
  - No new workflow failures
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 189) - CI/CD requirement
- **Dependencies**:
  - Task 4.2 completion

## Dependencies

- Node.js (installed in dev container)
- NPM (installed in dev container)
- Docker (for build verification)
- GitHub Actions (for CI/CD verification)

## Success Criteria

- Zero npm deprecation warnings for ESLint-related packages
- Zero npm deprecation warnings for transitive dependencies (glob, rimraf, inflight)
- esbuild vulnerability GHSA-67mh-4wv8-2f99 resolved
- ESLint 8 end-of-life warning eliminated
- All frontend tests passing
- Docker frontend build successful
- CI/CD pipeline green
- No new warnings or errors introduced
