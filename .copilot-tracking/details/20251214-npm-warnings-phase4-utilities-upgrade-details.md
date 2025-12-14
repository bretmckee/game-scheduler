<!-- markdownlint-disable-file -->

# Task Details: NPM Warnings Elimination Phase 4 - Routing & Utilities Upgrade

## Research Reference

**Source Research**: #file:../research/20251214-npm-warnings-elimination-research.md (Lines 132-146, 227-230)

## Phase 1: React Router Assessment

### Task 1.1: Audit React Router usage

Search codebase for React Router usage patterns.

- **Files**:
  - All files importing from 'react-router-dom'
  - Route configuration files
- **Success**:
  - Complete inventory of Router components used
  - List of all routes defined
  - Usage of data loading APIs (if any)
  - Custom hooks usage documented
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 132-137) - React Router migration details
- **Dependencies**:
  - None (assessment phase)

### Task 1.2: Review React Router v7 breaking changes

Review official React Router v7 migration guide.

- **Files**:
  - None (documentation review)
- **Success**:
  - List of breaking changes affecting this project
  - New data API patterns understood
  - Migration effort estimated
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 135) - New routing patterns, data APIs
  - #fetch:"https://reactrouter.com/en/main/upgrading/v6-v7" - Official upgrade guide
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Decide on React Router upgrade

Make go/no-go decision on React Router v7 upgrade.

- **Files**:
  - None (decision documentation)
- **Success**:
  - Decision documented: upgrade OR stay on v6
  - Rationale explained
  - Timeline estimate (if upgrading)
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 136) - MEDIUM-HIGH effort
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 228) - LOW priority
- **Dependencies**:
  - Task 1.2 completion

## Phase 2: date-fns Assessment

### Task 2.1: Audit date-fns usage

Search codebase for date-fns usage patterns.

- **Files**:
  - All files importing from 'date-fns'
- **Success**:
  - Complete list of date-fns functions used
  - Frequency of usage documented
  - Date formatting patterns identified
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 138-143) - date-fns migration details
- **Dependencies**:
  - None (assessment phase)

### Task 2.2: Review date-fns v4 breaking changes

Review date-fns v4 upgrade guide.

- **Files**:
  - None (documentation review)
- **Success**:
  - ESM-only requirement understood
  - Function signature changes documented
  - Migration effort estimated
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 141) - ESM-only, function signatures
  - #fetch:"https://date-fns.org/docs/Upgrade-Guide" - Official upgrade guide
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Decide on date-fns upgrade

Make go/no-go decision on date-fns v4 upgrade.

- **Files**:
  - None (decision documentation)
- **Success**:
  - Decision documented: upgrade OR stay on v2
  - Rationale explained
  - Timeline estimate (if upgrading)
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 142) - MEDIUM effort
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 229) - LOW priority
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: Implementation (If Proceeding)

### Task 3.1: Update package versions

Update React Router and/or date-fns package versions.

- **Files**:
  - `frontend/package.json`
- **Success**:
  - Packages updated to target versions
  - npm install completes successfully
  - No peer dependency conflicts
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 227-230) - Phase 4 tasks
- **Dependencies**:
  - Decision to proceed from Phase 1 and/or Phase 2

### Task 3.2: Migrate React Router code

Update code to React Router v7 patterns (if upgrading).

- **Files**:
  - All files using React Router
  - Route configuration files
- **Success**:
  - All routing code uses v7 APIs
  - Data loading migrated to new patterns
  - No deprecated API usage
  - Routing functionality preserved
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 135) - New routing patterns
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Migrate date-fns code

Update code to date-fns v4 patterns (if upgrading).

- **Files**:
  - All files using date-fns
- **Success**:
  - All date-fns imports use ESM syntax
  - Function calls updated to v4 signatures
  - Date formatting works correctly
  - No deprecation warnings
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 141) - ESM-only, function signatures
- **Dependencies**:
  - Task 3.1 completion

### Task 3.4: Run tests and verify functionality

Test all routing and date-related functionality.

- **Files**:
  - All test files
- **Success**:
  - All tests passing
  - Routing works correctly
  - Date formatting correct
  - No console warnings or errors
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 227-230) - Phase 4 requirements
- **Dependencies**:
  - Task 3.2 and/or Task 3.3 completion

## Dependencies

- Phases 1-3 completion recommended but not required
- Node.js (installed in dev container)
- NPM (installed in dev container)

## Success Criteria

**If deferring upgrades:**
- Decision rationale documented for each package
- Current versions functional
- No urgent migration need identified

**If upgrading React Router:**
- React Router v7 installed and functional
- All routing code migrated
- Tests passing
- No routing regressions

**If upgrading date-fns:**
- date-fns v4 installed and functional
- All date code migrated to ESM
- Date formatting works correctly
- Tests passing
