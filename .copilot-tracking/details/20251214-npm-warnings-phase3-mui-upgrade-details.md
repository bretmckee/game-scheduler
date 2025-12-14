<!-- markdownlint-disable-file -->

# Task Details: NPM Warnings Elimination Phase 3 - MUI Framework Upgrade

## Research Reference

**Source Research**: #file:../research/20251214-npm-warnings-elimination-research.md (Lines 123-131, 216-226)

## Phase 1: Impact Assessment

### Task 1.1: Audit MUI component usage

Search codebase for all Material-UI component usage to assess migration scope.

- **Files**:
  - All `frontend/src/**/*.tsx` files using MUI components
- **Success**:
  - Complete inventory of MUI components used
  - Count of component instances
  - Identification of custom MUI styling
  - Documentation of theme customization
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 123-126) - MUI migration effort HIGH
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 217-219) - Phase 3 evaluation step
- **Implementation Guidance**:
  - Search for imports from '@mui/material', '@mui/icons-material', '@mui/system'
  - List all unique MUI components
  - Note any direct @mui/base usage
  - Document styled() usage and sx prop patterns
- **Dependencies**:
  - Phase 2 (React upgrade) completion recommended

### Task 1.2: Review breaking changes documentation

Review official MUI migration guides for v5→v6 and v6→v7 breaking changes.

- **Files**:
  - None (documentation review)
- **Success**:
  - List of breaking changes affecting this project
  - Identification of deprecated APIs in use
  - Understanding of theming changes
  - Component prop changes documented
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 125) - Component API changes, theming updates
  - #fetch:"https://mui.com/material-ui/migration/upgrade-to-v6/" - Official v5→v6 guide
  - #fetch:"https://mui.com/material-ui/migration/upgrade-to-v7/" - Official v6→v7 guide
- **Implementation Guidance**:
  - Cross-reference breaking changes with component inventory
  - Identify high-risk changes
  - Document codemods available
  - Note any unsupported patterns
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Evaluate migration effort vs staying on v5 LTS

Make go/no-go decision on MUI v7 migration based on effort assessment.

- **Files**:
  - None (decision documentation)
- **Success**:
  - Decision documented: upgrade to v7 OR stay on v5 LTS
  - Rationale clearly explained
  - Risk assessment completed
  - Timeline estimate (if upgrading)
  - Alternative approaches considered
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 126) - HIGH migration effort
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 218-219) - Consider staying on v5 LTS option
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 220) - HIGH effort, deferred if not critical
- **Decision Criteria**:
  - If component usage is extensive: consider staying on v5 LTS
  - If heavy theme customization: consider staying on v5 LTS
  - If @mui/base deprecation is low-priority: defer migration
  - MUI v5 has LTS support, deprecation warning is informational only
- **Dependencies**:
  - Task 1.2 completion

## Phase 2: Dependency Updates (If Proceeding)

### Task 2.1: Update MUI core packages to v7

Update all Material-UI packages from v5 to v7.

- **Files**:
  - `frontend/package.json` - Update @mui/* packages
- **Success**:
  - package.json contains `"@mui/material": "^7.3.6"`
  - package.json contains `"@mui/icons-material": "^7.3.6"`
  - package.json contains `"@mui/system": "^7.3.6"` (if used)
  - @mui/base removed or replaced with @base-ui-components/react
  - No syntax errors in package.json
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 123-126) - MUI upgrade details
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 221-223) - Phase 3 migration tasks
- **Implementation Guidance**:
  - Update all @mui/* packages to ^7.3.6
  - Check for @emotion dependencies (may need updates)
  - Review peerDependencies warnings
- **Dependencies**:
  - Task 1.3 decision to proceed with upgrade

### Task 2.2: Install dependencies and verify versions

Run npm install and verify all MUI packages upgraded successfully.

- **Files**:
  - `frontend/package-lock.json` - Updated by npm install
  - `frontend/node_modules/` - Updated by npm install
- **Success**:
  - `npm list @mui/material` shows @mui/material@7.3.6
  - No @mui/base in dependency tree
  - No installation errors
  - All peer dependencies satisfied
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 221-223) - Phase 3 tasks
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Code Migration (If Proceeding)

### Task 3.1: Update theme configuration

Migrate MUI theme configuration to v7 API.

- **Files**:
  - Theme configuration file (e.g., `frontend/src/theme.tsx` or similar)
  - App component with ThemeProvider
- **Success**:
  - Theme configuration uses v7 API
  - No deprecated theme properties
  - Theme applies correctly in development
  - No theme-related console warnings
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 125) - Theming updates
- **Implementation Guidance**:
  - Review createTheme() API changes
  - Update palette, typography, spacing if changed
  - Check for deprecated theme properties
  - Test ThemeProvider integration
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Migrate deprecated component APIs

Update all MUI components using deprecated APIs to v7 patterns.

- **Files**:
  - Components identified in Task 1.1 with deprecated APIs
- **Success**:
  - All components use v7 APIs
  - No deprecated prop warnings
  - Component functionality unchanged
  - No console warnings
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 125) - Component API changes
- **Implementation Guidance**:
  - Run MUI codemods if available
  - Update deprecated props manually
  - Test each component after changes
  - Check for renamed components
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Update styled components and sx props

Migrate any styled() usage and sx prop patterns to v7 API.

- **Files**:
  - Components with styled() or heavy sx prop usage
- **Success**:
  - All styled() calls use v7 API
  - sx props work correctly
  - Styling visually consistent
  - No styling-related console warnings
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 125) - Component API changes
- **Implementation Guidance**:
  - Check styled() import source
  - Review @emotion/styled vs @mui/system
  - Test responsive sx props
  - Verify theme access in styled components
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Fix TypeScript type errors

Address TypeScript compilation errors from MUI v7 type changes.

- **Files**:
  - All files with MUI-related TypeScript errors
- **Success**:
  - `npm run build` completes with zero TypeScript errors
  - Component props properly typed
  - Theme types correct
  - No type cast workarounds needed
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 125) - Breaking changes
- **Dependencies**:
  - Task 3.3 completion

## Phase 4: Testing & Validation (If Proceeding)

### Task 4.1: Visual regression testing

Manually compare UI appearance before and after MUI upgrade.

- **Files**:
  - None (manual visual testing)
- **Success**:
  - UI visually consistent with v5
  - No layout shifts or broken layouts
  - Colors and typography match
  - Icons render correctly
  - Responsive behavior maintained
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 224) - Testing requirement
- **Implementation Guidance**:
  - Take screenshots before upgrade
  - Compare side-by-side after upgrade
  - Test all major pages/components
  - Check mobile and desktop views
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Run unit test suite

Execute all frontend tests to ensure MUI v7 compatibility.

- **Files**:
  - All test files
- **Success**:
  - `npm test` passes all tests
  - No MUI-related test failures
  - Test coverage maintained
  - No new console warnings in tests
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 224) - Testing requirement
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Manual UI testing

Perform comprehensive manual testing of all UI interactions.

- **Files**:
  - None (manual testing)
- **Success**:
  - All user workflows functional
  - Buttons, forms, dialogs work correctly
  - No interaction bugs
  - Performance acceptable
  - No console errors
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 224) - Testing requirement
- **Implementation Guidance**:
  - Test all forms
  - Test all modals/dialogs
  - Test navigation
  - Test data display components
  - Verify accessibility features
- **Dependencies**:
  - Task 4.2 completion

### Task 4.4: Verify Docker builds

Build frontend Docker image with MUI v7.

- **Files**:
  - `docker/frontend.Dockerfile`
  - `compose.yaml`
- **Success**:
  - `docker compose build frontend` completes successfully
  - No build errors or warnings
  - Image size reasonable
  - Production build works
- **Research References**:
  - #file:../research/20251214-npm-warnings-elimination-research.md (Lines 224) - Testing requirement
- **Dependencies**:
  - Task 4.3 completion

## Dependencies

- Phase 1 (Vite/ESLint upgrade) must be completed
- Phase 2 (React upgrade) should be completed first
- Node.js (installed in dev container)
- NPM (installed in dev container)
- Docker (for build verification)

## Success Criteria

**If staying on MUI v5 LTS:**
- Decision rationale documented
- v5 LTS support timeline verified
- @mui/base deprecation warning accepted (low priority)
- No code changes required

**If upgrading to MUI v7:**
- MUI upgraded to v7.3.6
- @mui/base deprecation eliminated
- All component APIs updated
- Zero TypeScript compilation errors
- UI visually consistent with v5
- All tests passing
- Docker frontend build successful
- No new warnings or errors
