<!-- markdownlint-disable-file -->
# Task Research Notes: TypeScript Tooling Setup for Local Development

## Research Executed

### File Analysis
- `frontend/package.json`
  - Project uses TypeScript 5.3.3, Vite 5.0.8, ESLint 8.55.0
  - Already has ESLint configured with TypeScript, React, and Prettier plugins
  - Scripts defined: `dev`, `build` (tsc && vite build), `lint`, `lint:fix`, `type-check`
  - Dependencies managed via npm (package.json present, no lock file analysis needed)

- `frontend/.eslintrc.cjs`
  - Complete ESLint configuration already exists
  - Uses TypeScript parser (@typescript-eslint/parser)
  - Integrates Prettier for code formatting
  - Configured for React 18.2+ with jsx-runtime

- `frontend/tsconfig.json`
  - Target: ES2022, module: ESNext
  - Strict mode enabled with additional safety checks
  - Path mapping configured (@/* -> ./src/*)

- `docker/frontend.Dockerfile`
  - Uses Node.js 20-alpine in build stage
  - Runs `npm ci` for dependency installation
  - Build command: `npm run build`

### Code Search Results
- No Node.js tooling currently installed on system
- Docker uses Node.js 20-alpine
- Project has no `.nvmrc` or `.node-version` file to specify Node version

### External Research
- #githubRepo:"nvm-sh/nvm nvm installation usage"
  - nvm is the most established Node version manager (89.9k stars)
  - Bash script-based, POSIX-compliant
  - Installs to `~/.nvm` by default
  - Installation: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash`
  - Usage: `nvm install 20`, `nvm use 20`, `nvm alias default 20`
  - Supports `.nvmrc` files for project-specific versions
  - Auto-loads Node versions when entering directories (with shell integration)

- #githubRepo:"Schniz/fnm fast node manager"
  - Fast Node Manager built in Rust (22.8k stars)
  - Single binary, faster startup than nvm
  - Installation: `curl -fsSL https://fnm.vercel.app/install | bash` or `brew install fnm`
  - Cross-platform (macOS, Linux, Windows)
  - Supports `.node-version` and `.nvmrc` files
  - Auto-switching with `--use-on-cd` flag
  - Usage: `fnm install 20`, `fnm use 20`, `fnm default 20`

- #githubRepo:"volta-cli/volta node version manager"
  - Volta is unmaintained as of issue #2080 (12.6k stars)
  - Recommend migrating to mise instead
  - Not a viable option for new setups

- #githubRepo:"nodejs/corepack package manager version manager"
  - Corepack is built into Node.js 14.19.0 - 24.x
  - Zero-runtime-dependency tool for managing package managers (npm, yarn, pnpm)
  - Enables per-project package manager versions via `packageManager` field in package.json
  - Usage: `corepack enable` to install yarn and pnpm shims
  - Uses `packageManager` field to enforce specific versions with integrity hashes

- #fetch:"https://pnpm.io/"
  - pnpm is 2x faster than npm with efficient disk space usage
  - Hard links packages from global store instead of duplicating
  - Creates strict non-flat node_modules (better dependency isolation)
  - Built-in monorepo support
  - Installation: `npm install -g pnpm` or via corepack
  - Commands identical to npm: `pnpm install`, `pnpm add`, `pnpm run`

### Project Conventions
- Standards referenced: `.github/instructions/reactjs.instructions.md`
  - React 19+ with TypeScript
  - Functional components with hooks
  - Vite as build tool
- Instructions followed: `.github/instructions/typescript-5-es2022.instructions.md`
  - TypeScript 5.x targeting ES2022
  - Strict mode enabled
  - Modern module resolution

## Key Discoveries

### Project Structure
- Frontend is a standalone TypeScript/React/Vite project in `frontend/` directory
- Backend uses Python with uv for dependency management
- No monorepo setup currently
- ESLint already fully configured and integrated with package scripts

### Implementation Patterns
- Package manager: npm (based on `npm ci` in Dockerfile and npm scripts in package.json)
- Build tool: Vite with TypeScript pre-compile step
- Testing: Vitest configured
- Linting: ESLint with TypeScript, React, and Prettier plugins

### Complete Examples

#### Node Version Manager Setup with nvm
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

# Add to ~/.bashrc (auto-added by install script)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Install Node.js 20 (matches Docker)
nvm install 20
nvm alias default 20
nvm use 20

# Verify installation
node --version  # v20.x.x
npm --version   # 10.x.x
```

#### Alternative: Fast Node Manager (fnm)
```bash
# Install fnm (faster alternative)
curl -fsSL https://fnm.vercel.app/install | bash

# Add to ~/.bashrc
eval "$(fnm env --use-on-cd --shell bash)"

# Install Node.js 20
fnm install 20
fnm default 20

# Verify
node --version
```

#### Running TypeScript and Vite Commands
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (creates isolated node_modules in frontend/)
npm install

# Run development server
npm run dev

# Type checking
npm run type-check

# Run linter
npm run lint

# Fix linting issues
npm run lint:fix

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test
```

### API and Schema Documentation
- Node.js provides npm as the default package manager
- npm creates isolated `node_modules` per project (acts like virtual environment)
- Global packages can be installed with `-g` flag but project deps are local
- Each project has its own dependency tree in `node_modules/`

### Configuration Examples

#### Create .nvmrc for project version pinning
```bash
# In project root, specify Node version
echo "20" > .nvmrc

# Now nvm/fnm will auto-use this version in project directory
```

#### Update package.json with engines field
```json
{
  "engines": {
    "node": ">=20.0.0",
    "npm": ">=10.0.0"
  }
}
```

#### Use Corepack for package manager version locking (optional)
```json
{
  "packageManager": "npm@10.2.3"
}
```

```bash
# Enable corepack (built into Node.js)
corepack enable

# Now npm version will be enforced per package.json
```

### Technical Requirements
**Minimal Installation Requirements:**
1. Node.js version manager (nvm or fnm)
2. Node.js 20.x (to match Docker environment)
3. npm (included with Node.js)

**That's it!** No additional tools needed. npm handles dependency isolation.

**Node.js Dependency Isolation:**
- Each project has isolated `node_modules/` directory
- Dependencies installed via `npm install` are project-local by default
- Global installs (`npm install -g`) are separate and optional
- No need for virtualenv-style tool; npm handles isolation automatically
- Multiple projects can use different dependency versions without conflicts

## Recommended Approach

**Use fnm as Node version manager** (faster, simpler, Rust-based) with project-local npm dependencies.

### Installation Steps:
1. Install fnm for Node version management
2. Install Node.js 20 to match Docker environment
3. Use npm (included with Node.js) for dependency management
4. Create `.nvmrc` or `.node-version` file to document version
5. ESLint is already configured - no additional setup needed

### Why fnm over nvm:
- Faster installation and switching (written in Rust vs Bash)
- Simpler codebase and fewer dependencies
- Cross-platform support including Windows
- Compatible with nvm's `.nvmrc` files
- Active maintenance and modern design

### Why npm over pnpm/yarn:
- Project already uses npm (Dockerfile, no lock files for other managers)
- npm provides isolated node_modules per project
- No migration needed
- Sufficient for project's needs

### ESLint Status:
- Already fully configured in `.eslintrc.cjs`
- Integrated with TypeScript parser
- Prettier integration for formatting
- React-specific rules configured
- Scripts already in package.json (`npm run lint`, `npm run lint:fix`)

## Implementation Guidance

### Objectives
- Enable local TypeScript compilation and Vite development server
- Provide isolated dependency management per project
- Match Docker Node.js version for consistency
- Ensure linting works locally

### Key Tasks
1. Install fnm Node version manager
2. Install Node.js 20.x using fnm
3. Create `.nvmrc` file in project root with "20"
4. Navigate to `frontend/` and run `npm install`
5. Verify with `npm run type-check` and `npm run lint`
6. Test dev server with `npm run dev`

### Dependencies
- curl or wget (for fnm installation)
- bash shell (already available)

### Success Criteria
- `node --version` shows v20.x.x
- `npm --version` shows 10.x.x
- `tsc --version` shows TypeScript version (from node_modules)
- `npm run dev` starts Vite dev server on http://localhost:3000
- `npm run lint` executes ESLint successfully
- `npm run build` compiles TypeScript and builds production assets
