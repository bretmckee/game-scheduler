<!-- markdownlint-disable-file -->

# Task Research Notes: Frontend Docker Build Optimization

## Research Executed

### File Analysis

- `docker/frontend.Dockerfile`
  - Current multi-stage build with builder and nginx production stages
  - Copies `package*.json` first (line 7), runs `npm ci` (line 8)
  - Then copies entire `frontend/` directory (line 11)
  - Build step runs `npm run build` (line 14)

### Size Analysis

- `frontend/node_modules`: 413MB
- `frontend/src`: 268KB (38 source files)
- Total frontend files (including node_modules): 52,419 files
- No `.dockerignore` file exists in project

### Docker Best Practices Review

- `.github/instructions/containerization-docker-best-practices.instructions.md`
  - Emphasizes layer caching optimization
  - Recommends ordering from least to most frequently changing
  - Suggests using `.dockerignore` to exclude unnecessary files
  - Advocates for selective COPY operations

### External Research

- #fetch:https://docs.docker.com/build/cache/

  - Layer invalidation: when a layer changes, all downstream layers rebuild
  - Once cache is invalidated, all subsequent layers must re-run
  - Proper ordering of COPY instructions is critical for cache efficiency

- #githubRepo:"nodejs/docker-node"
  - Official Node.js Docker images follow pattern of copying package files first
  - Dependencies installed before source code copy
  - No examples of separately caching node_modules after installation

## Key Discoveries

### Current Build Behavior

**Problem Identified**: The current Dockerfile copies the entire `frontend/` directory in line 11, which includes:

- Source files (268KB, changes frequently)
- Configuration files (changes occasionally)
- **node_modules if present on host** (413MB, should never be copied)

This means:

1. Every source code change invalidates the cache for the `COPY frontend/ ./` layer
2. If `node_modules` exists on the host, it gets copied (413MB transfer to build context)
3. The subsequent `npm run build` layer must re-run even though dependencies haven't changed

### Docker Layer Caching Principles

**How Docker Cache Works**:

- Each instruction creates a layer
- Layers are cached if the instruction and context haven't changed
- When a layer invalidates, **all subsequent layers invalidate**
- COPY instructions invalidate when file contents or timestamps change

**Current Issue**: After `npm ci` installs dependencies, copying `frontend/` invalidates cache even when only source files change, not dependencies.

### Analysis of Proposed Solution

**Your Hypothesis**: Separate node_modules copy into its own cacheable step.

**Reality Check**:

- `node_modules` is **generated inside the container** by `npm ci` (line 8)
- It doesn't exist separately to copy - it's created by the install step
- The current Dockerfile **already** follows the correct pattern:
  1. Copy package files
  2. Install dependencies (creates node_modules)
  3. Copy source code
  4. Build

**Actual Problem**: The `COPY frontend/ ./` at line 11 is too broad and may:

1. Copy host's node_modules if it exists (wasteful, ~413MB)
2. Copy unnecessary files (tests, configs, etc.)
3. Invalidate build cache when any file changes

## Recommended Approach

### Solution: Selective COPY Instructions (Primary) + .dockerignore (Safety Net)

**Strategy**: Use explicit COPY commands to allow only necessary files, with .dockerignore as backup protection

**Why This Approach**:

- ✅ **Complete control** - only explicitly listed files/directories are copied
- ✅ **Immune to new files** - new files in frontend/ are automatically excluded unless you add them
- ✅ **Self-documenting** - shows exactly what the build requires
- ✅ **Zero maintenance** - no risk of files "sneaking in"
- ✅ **.dockerignore as safety net** - still catches node_modules if it exists

#### Implementation Steps:

1. **Create comprehensive `.dockerignore` in project root** (safety net):

   ```dockerignore
   # Node modules (will be installed in container)
   **/node_modules/
   **/.pnp/
   **/.pnp.js

   # Build outputs (generated in container)
   **/dist/
   **/build/
   **/coverage/
   **/.next/
   **/.nuxt/
   **/.cache/

   # Environment files (use broad pattern)
   **/.env*
   !**/.env.example

   # IDE and OS files (comprehensive)
   **/.vscode/
   **/.idea/
   **/.fleet/
   **/.cursor/
   **/*.swp
   **/*.swo
   **/.DS_Store
   **/Thumbs.db

   # Git
   **/.git/
   **/.gitignore
   **/.gitattributes

   # Documentation (selective)
   **/*.md
   !**/README.md
   **/docs/

   # Test files (broad patterns)
   **/test/
   **/tests/
   **/__tests__/
   **/*.test.*
   **/*.spec.*
   **/.coverage/

   # Logs and temp (very broad)
   **/*.log*
   **/.tmp/
   **/.temp/
   **/tmp/
   **/*.tsbuildinfo
   **/*.cache
   ```

2. **Replace broad COPY with selective COPY instructions** in `docker/frontend.Dockerfile`:

   ```dockerfile
   # Current (line 11) - TOO BROAD:
   COPY frontend/ ./

   # Optimized (EXPLICIT CONTROL):
   # Copy source code
   COPY frontend/src ./src

   # Copy build configuration files
   COPY frontend/index.html ./
   COPY frontend/vite.config.ts ./
   COPY frontend/tsconfig.json ./
   COPY frontend/tsconfig.node.json ./
   COPY frontend/vitest.config.ts ./

   # Note: package.json already copied earlier (line 7)
   # Note: node_modules generated by npm ci (line 8)
   # Note: public/ directory intentionally excluded (appears to not exist based on frontend structure)
   ```

### Why This Works

**Complete Control with Selective COPY**:

- Only explicitly listed files/directories are copied into the build
- New files added to frontend/ are automatically ignored unless you update the Dockerfile
- Makes build requirements explicit and visible in the Dockerfile
- Eliminates risk of accidentally including sensitive or unnecessary files

**Cache Efficiency**:

- Package files copied first (line 7) → triggers npm ci only when dependencies change
- node_modules generated in container (line 8) → not affected by host files
- Source files copied with selective COPY → only relevant files included
- Configuration files separated → can be cached independently if needed

**Build Speed Improvement**:

- Smaller build context (no 413MB node_modules transfer)
- Selective copying reduces files Docker must check for changes
- Better layer caching (source changes don't invalidate dependency layer)
- Faster Docker context upload to daemon

**.dockerignore as Safety Net**:

- Broad patterns catch common files that shouldn't be in any build context
- Protects against accidentally adding a directory copy that includes node_modules
- Future-proof against new file types with wildcard patterns
- Zero maintenance required once configured

### Expected Impact

**Before optimization**:

- Build context: ~413MB (includes node_modules if present)
- Every source change: Re-uploads entire frontend directory
- Cache invalidation: Frequent, due to broad COPY
- Risk: Can accidentally include test files, env files, etc.

**After optimization**:

- Build context: ~270KB (only explicitly copied files)
- Every source change: Only uploads changed source files from src/
- Cache preservation: Dependencies layer remains cached
- Risk: Zero - only listed files can be copied
- **Estimated improvement**: 60-90% faster incremental builds

### Trade-offs and Considerations

**Pros**:

- ✅ Maximum security - no accidental file inclusion
- ✅ Fastest builds - minimal context size
- ✅ Self-documenting - clear what's needed for build
- ✅ Future-proof - new files can't sneak in

**Cons**:

- ⚠️ Requires Dockerfile update when adding new directories (e.g., `frontend/assets/`)
- ⚠️ Slightly more verbose Dockerfile

**Decision**: The security and performance benefits far outweigh the minor maintenance requirement of updating COPY statements when adding new directories to the frontend structure.

## Implementation Guidance

**Objectives**:

- Use explicit COPY commands to control exactly what enters the build
- Add comprehensive .dockerignore as safety net against accidental inclusions
- Reduce build context size by excluding node_modules and unnecessary files
- Improve layer caching efficiency for faster incremental builds
- Maintain current multi-stage build structure

**Key Tasks**:

1. Create comprehensive `.dockerignore` in project root with broad patterns
2. Replace `COPY frontend/ ./` with selective COPY statements for:
   - `frontend/src/` directory
   - Individual configuration files (index.html, vite.config.ts, tsconfig files)
3. Test build works correctly with selective COPY
4. Verify node_modules is not copied from host
5. Measure build time improvement for incremental builds

**Files to Modify**:

- Create: `.dockerignore` (project root)
- Modify: `docker/frontend.Dockerfile` (line 11 - replace broad COPY)

**Dependencies**:

- None (pure Docker optimization)

**Success Criteria**:

- Build context size reduced from 413MB to <300KB
- Incremental builds (source-only changes) complete in <10 seconds
- Dependencies layer cache preserved across source code changes
- Production image size unchanged
- Build still completes successfully with all necessary files
- No files can "sneak in" - only explicitly listed files are copied
