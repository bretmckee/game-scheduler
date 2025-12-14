<!-- markdownlint-disable-file -->

# Task Details: NPM Warnings Elimination Phase 2 - React Ecosystem Upgrade

## Research Reference

**Source Research**: #file:../research/20251214-npm-warnings-elimination-research.md (Lines 115-122)

## Phase 1: Dependency Updates

### Task 1.1: Update React core packages

Update React and React DOM from 18.3.1 to 19.2.3.

- **Files**:
  - `frontend/package.json` - Update "react" and "react-dom" versions
- **Success**:
  - package.json contains `"react": "^19.2.3"`
  - package.json contains `"react-dom": "^19.2.3"`
  - No syntax errors in package.json
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 115-122) - React 19 migration details
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 204-210) - Phase 2 implementation guidance
- **Dependencies**:
  - Phase 1 (Vite/ESLint upgrade) completion

### Task 1.2: Update React type definitions

Update TypeScript type definitions for React 19 compatibility.

- **Files**:
  - `frontend/package.json` - Update "@types/react" and "@types/react-dom"
- **Success**:
  - package.json contains `"@types/react": "^19.0.0"`
  - package.json contains `"@types/react-dom": "^19.0.0"`
  - Type definitions compatible with React 19
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 118-119) - TypeScript definition changes
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 207) - Type update requirement
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Update React Testing Library

Update React Testing Library to version compatible with React 19.

- **Files**:
  - `frontend/package.json` - Update "@testing-library/react"
- **Success**:
  - package.json contains `"@testing-library/react": "^16.0.0"` or higher
  - Testing library compatible with React 19
  - No peer dependency warnings
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 208) - Testing library update
- **Dependencies**:
  - Task 1.2 completion

### Task 1.4: Install dependencies and verify versions

Run npm install and verify all React packages are at correct versions.

- **Files**:
  - `frontend/package-lock.json` - Updated by npm install
  - `frontend/node_modules/` - Updated by npm install
- **Success**:
  - `npm list react` shows react@19.2.3
  - `npm list react-dom` shows react-dom@19.2.3
  - No installation errors or warnings
  - All peer dependencies satisfied
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 204-210) - Phase 2 tasks
- **Dependencies**:
  - Task 1.3 completion

## Phase 2: Code Migration

### Task 2.1: Audit ref usage patterns

Search codebase for ref usage that may be affected by React 19 changes.

- **Files**:
  - All `frontend/src/**/*.tsx` files with ref usage
- **Success**:
  - List of all components using refs identified
  - Legacy ref patterns documented
  - String refs identified (if any)
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 118) - Ref handling breaking changes
- **Implementation Guidance**:
  - Search for `React.createRef`, `useRef`, `forwardRef`
  - Look for callback refs with cleanup
  - Identify string refs (deprecated, unlikely in modern code)
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Update deprecated ref callbacks

Update any ref callback patterns that changed in React 19.

- **Files**:
  - Components identified in Task 2.1 with deprecated patterns
- **Success**:
  - All ref callbacks follow React 19 patterns
  - No deprecated ref usage warnings
  - Refs work correctly in development mode
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 118) - Ref handling changes
- **Implementation Guidance**:
  - React 19 may call ref cleanup differently
  - Ensure ref callbacks handle null properly
  - Update forwardRef usage if needed
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Fix TypeScript type errors

Address any TypeScript compilation errors from React 19 type changes.

- **Files**:
  - All `frontend/src/**/*.tsx` files with type errors
  - `frontend/src/**/*.ts` files with React type usage
- **Success**:
  - `npm run build` completes with zero TypeScript errors
  - All component props properly typed
  - No type cast workarounds needed
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 119) - TypeScript definition changes
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: Testing & Validation

### Task 3.1: Run unit test suite

Execute all frontend unit tests to ensure React 19 compatibility.

- **Files**:
  - All `frontend/src/**/*.test.tsx` test files
- **Success**:
  - `npm test` passes all tests
  - No new test failures
  - Test coverage maintained
  - No React 19 deprecation warnings in test output
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 209) - Testing effort requirement
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Run integration tests

Execute integration test suite to validate component interactions.

- **Files**:
  - Integration test files in test directories
- **Success**:
  - All integration tests pass
  - No React 19 related failures
  - Component interactions work correctly
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 209) - Testing requirements
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Manual UI testing

Perform manual testing of key user workflows in development mode.

- **Files**:
  - None (manual testing)
- **Success**:
  - All key user workflows functional
  - No visual regressions
  - No console errors or warnings
  - Performance acceptable
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 209) - Performance improvements note
- **Implementation Guidance**:
  - Test game scheduling workflows
  - Test authentication flows
  - Test form submissions
  - Check for any UI glitches
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Verify Docker builds

Build frontend Docker image to ensure production builds work with React 19.

- **Files**:
  - `docker/frontend.Dockerfile`
  - `compose.yaml`
- **Success**:
  - `docker compose build frontend` completes successfully
  - No build errors or warnings
  - Image size remains reasonable
  - Production build optimizations work
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 204-210) - Phase 2 completion criteria
- **Dependencies**:
  - Task 3.3 completion

## Dependencies

- Phase 1 (Vite/ESLint upgrade) must be completed
- Node.js (installed in dev container)
- NPM (installed in dev container)
- Docker (for build verification)

## Success Criteria

- React upgraded to 19.2.3
- All React type definitions updated
- Zero TypeScript compilation errors
- All unit tests passing
- All integration tests passing
- No runtime errors in development
- Docker frontend build successful
- No new console warnings or errors
