<!-- markdownlint-disable-file -->
# Task Research Notes: NPM Warnings Elimination

## Research Executed

### NPM Warning Analysis
- `npm ci` output analysis
  - 6 deprecated package warnings identified
  - 2 moderate severity vulnerabilities (esbuild)
  - Multiple dependency version warnings

### Package Analysis
- `npm outdated` review
  - Major version updates available for key packages (ESLint 8→9, React 18→19, MUI 5→7)
  - Minor version updates available for several packages
  - Breaking changes expected for major version upgrades

### Vulnerability Analysis
- #fetch:"https://github.com/advisories/GHSA-67mh-4wv8-2f99"
  - esbuild ≤0.24.2 CORS vulnerability (CVSSv3: 5.3 Moderate)
  - Fixed in esbuild 0.25.0
  - Only affects development server with serve feature
  - Allows malicious websites to read dev server responses via CORS misconfiguration

### Code Search Results
- `vite.config.ts` review
  - Uses Vite dev server, not direct esbuild serve
  - Standard proxy configuration for API
  - No custom esbuild serve configuration

### Package Dependencies
- `npm list esbuild`
  - vite@5.4.21 → esbuild@0.21.5 (vulnerable)
 vite@7.2.2 → esbuild@0.25.12 (patched)
  - Dual versions installed due to Vite v5/v7 coexistence

## Key Discoveries

### Deprecated Packages
1. **inflight@1.0.6** - Memory leak, no longer supported
   - Transitive dependency
   - Recommendation: Use lru-cache instead

2. **@humanwhocodes/config-array@0.13.0** - Replaced by @eslint/config-array
   - ESLint 8 dependency
   - Fixed by upgrading to ESLint 9

3. **rimraf@3.0.2** - Version <4 no longer supported
   - Transitive dependency
   - Automatically resolved with dependency updates

4. **glob@7.2.3** - Version <9 no longer supported
   - Transitive dependency
   - Automatically resolved with dependency updates

5. **@humanwhocodes/object-schema@2.0.3** - Replaced by @eslint/object-schema
   - ESLint 8 dependency
   - Fixed by upgrading to ESLint 9

6. **eslint@8.57.1** - No longer supported
   - Explicit devDependency
   - ESLint 9 available with breaking changes

7. **@mui/base@5.0.0-dev** - Replaced by @base-ui-components/react
   - Transitive dependency from MUI v5
   - Fixed by upgrading to MUI v7

### Security Vulnerabilities

**esbuild CORS Vulnerability (GHSA-67mh-4wv8-2f99)**
- **Severity**: Moderate (CVSSv3: 5.3)
- **Impact**: Development server only
- **Risk Level**: LOW for production (not deployed)
- **Risk Level**: LOW for development (requires attacker to know dev server URL and active session)
- **Attack Requirements**:
  - User must be running local dev server
  - User must visit malicious website simultaneously
  - Attacker must know local dev server URL/port
  - Only exposes local development code (not production secrets)
- **Current State**: vite@5.4.21 uses vulnerable esbuild@0.21.5
- **Fix**: Upgrade vite to v6+ (uses esbuild@0.25+)

### Version Update Analysis

**Critical Updates (Breaking Changes)**

1. **ESLint 8.57.1 → 9.39.2**
   - Status: End of life, security risk
   - Impact: HIGH priority
   - Breaking Changes: Flat config required, plugin API changes
   - Migration Effort: MEDIUM

2. **React 18.3.1 → 19.2.3**
   - Status: Stable major release
   - Impact: MEDIUM priority
   - Breaking Changes: Ref handling, TypeScript definitions
   - Migration Effort: LOW-MEDIUM

3. **MUI 5.18.0 → 7.3.6**
   - Status: Major version jump (2 versions)
   - Impact: MEDIUM priority
   - Breaking Changes: Component API changes, theming updates
   - Migration Effort: HIGH

4. **React Router 6.30.2 → 7.10.1**
   - Status: Major version release
   - Impact: MEDIUM priority
   - Breaking Changes: New routing patterns, data APIs
   - Migration Effort: MEDIUM-HIGH

5. **date-fns 2.30.0 → 4.1.0**
   - Status: Major version jump (2 versions)
   - Impact: LOW priority
   - Breaking Changes: ESM-only, function signatures
   - Migration Effort: MEDIUM

**Important Updates (Non-Breaking)**

6. **Vite 5.4.21 → 6.x (or 7.2.7)**
   - Status: Active development
   - Impact: HIGH priority (fixes esbuild vulnerability)
   - Breaking Changes: Minor config changes
   - Migration Effort: LOW

7. **TypeScript ESLint 6.21.0 → 8.49.0**
   - Status: Follows ESLint 9 migration
   - Impact: HIGH priority
   - Breaking Changes: Tied to ESLint 9
   - Migration Effort: MEDIUM

## Recommended Approach

### Phased Migration Strategy

**Phase 1: Security & Maintenance (IMMEDIATE)**
- Upgrade Vite 5 → 6 (fixes esbuild vulnerability)
- Upgrade ESLint 8 → 9 (end of life, security)
- Update TypeScript ESLint plugins
- Update minor version packages (prettier, vitest, jsdom)
- Impact: Minimal breaking changes, immediate security benefit

**Phase 2: React Ecosystem (SHORT-TERM)**
- Upgrade React 18 → 19
- Update @types/react, @types/react-dom
- Update @testing-library/react
- Impact: Moderate testing effort, improved performance

**Phase 3: UI Framework (MEDIUM-TERM)**
- Evaluate MUI 5 → 7 migration effort
- Consider staying on MUI v5 LTS if migration cost is high
- Assess breaking changes in detail
- Impact: High effort, deferred if not critical

**Phase 4: Routing & Utilities (LOW-PRIORITY)**
- Evaluate React Router 7 migration
- Consider date-fns v4 migration
- Impact: Low priority, functional on current versions

### Implementation Guidance

**Phase 1 Tasks**
1. Create feature branch for Phase 1 updates
2. Update Vite 5 → 6
   - Update `package.json`: `"vite": "^6.0.0"`
   - Run `npm install`
   - Test dev server, build, preview
   - Verify esbuild version ≥0.25.0
3. Migrate ESLint 8 → 9
   - Install ESLint 9 and new config format
   - Convert `.eslintrc.js` to `eslint.config.js` (flat config)
   - Update `@typescript-eslint/*` packages to v8
   - Update `eslint-plugin-*` packages to ESLint 9 compatible versions
   - Test linting across codebase
4. Update supporting packages
   - `prettier`: 3.6.2 → 3.7.4
   - `vitest`: 4.0.10 → 4.0.15
   - `jsdom`: 27.2.0 → 27.3.0
   - `eslint-plugin-react-refresh`: 0.4.24 → 0.4.25
5. Run full test suite
6. Verify CI/CD pipeline passes
7. Create PR with detailed migration notes

**Dependencies**: None (independent phase)

**Success Criteria**:
- All npm deprecation warnings eliminated except MUI/React/Router
- esbuild vulnerability resolved
- ESLint security issue resolved
- All tests passing
- CI/CD pipeline green
- No new warnings introduced

**Risk Mitigation**:
- Test extensively in development environment
- Run full integration test suite
- Verify Docker builds still work
- Review ESLint flat config migration guide carefully
- Keep Vite 5 config as reference during migration

**Estimated Effort**: 4-6 hours
- Vite upgrade: 30 minutes
- ESLint 9 migration: 2-3 hours (config conversion, plugin updates)
- Testing & validation: 1-2 hours
- Documentation: 30 minutes
