# Version Management

## Overview

The Game Scheduler uses **setuptools-scm** to automatically extract version information from git tags during the build process. No manual version setting required!

## Version Information

The system tracks two types of versions:

1. **Git Version**: Automatically derived from git tags (e.g., `0.0.1.dev478+gd128f6a`)
   - Extracted by setuptools-scm from `git describe --tags`
   - Uniquely identifies the deployed code
   - Updated automatically on every commit

2. **API Version**: Semantic version for API compatibility (e.g., `1.0.0`)
   - Manually updated in `shared/version.py`
   - Changes only for breaking API changes
   - Used by clients to check compatibility

## Accessing Version Information

### API Endpoints

**Version Endpoint** (`/api/v1/version`):
```json
{
  "service": "api",
  "git_version": "0.0.1.dev478+gd128f6a",
  "api_version": "1.0.0",
  "api_prefix": "/api/v1"
}
```

**Health Endpoint** (`/health`):
```json
{
  "status": "healthy",
  "service": "api",
  "version": {
    "git": "0.0.1.dev478+gd128f6a",
    "api": "1.0.0"
  }
}
```

### Web Interface

Access version information through the **About** page in the web interface:
- Navigate to the "About" link in the top navigation
- Displays version, copyright, and license information

## Building with Automatic Versioning

### Development or Production - Same Command!

```bash
# Version is automatically extracted from git - no environment variables needed!
docker compose build api
docker compose up
```

That's it! setuptools-scm automatically:
- Reads your git tags
- Counts commits since last tag
- Adds commit hash
- Handles dirty working directory

### How It Works

1. **Docker mounts `.git` directory** during build (read-only, not copied into image)
2. **setuptools-scm reads git metadata** during `pip install`
3. **Version is embedded in installed package**
4. **Python code reads it via `importlib.metadata.version()`**

No manual steps, no environment variables, no version files to maintain!

## Implementation Details

### Automatic Version Extraction

**pyproject.toml configuration:**
```toml
[build-system]
requires = ["setuptools>=80", "setuptools-scm[simple]>=8"]
build-backend = "setuptools.build_meta"

[project]
dynamic = ["version"]

[tool.setuptools_scm]
fallback_version = "0.0.0+unknown"
```

### Python Backend

Version information is provided by `shared/version.py`:

```python
from shared.version import get_git_version, get_api_version

git_version = get_git_version()    # From package metadata (setuptools-scm)
api_version = get_api_version()     # From API_VERSION constant
```

The module tries three sources in order:
1. **Package metadata** (setuptools-scm) - primary method
2. **GIT_VERSION env var** - fallback for special cases
3. **"dev-unknown"** - last resort

The FastAPI application includes version in:
- Application metadata (visible in OpenAPI docs at `/docs`)
- Health check endpoint
- Dedicated version endpoint

### Docker Configuration

The Dockerfile uses a git mount to provide version info:

```dockerfile
# Mount .git directory during package installation
RUN --mount=source=.git,target=.git,type=bind \
    uv pip install --system .
```

This mount is:
- **Read-only** - .git is not modified
- **Temporary** - .git is NOT included in the final image
- **Secure** - Only used during build, not in runtime container

### Frontend

The React frontend fetches version information from `/api/v1/version` and displays it on the About page.

## Updating API Version

When making breaking changes to the API:

1. Update `API_VERSION` in `shared/version.py`
2. Consider creating a new API version prefix (e.g., `/api/v2/`)
3. Document breaking changes
4. Communicate version requirements to API consumers

## Git Tagging Strategy

setuptools-scm works with standard semantic versioning tags:

```bash
# Create release tag
git tag v1.0.0
git push origin v1.0.0

# Development versions are automatically numbered
# After v1.0.0, commits automatically become:
# v1.0.0-1-gABCDEF (1 commit after v1.0.0)
# v1.0.0-2-gXYZ123 (2 commits after v1.0.0)
```

**Version Format:**
- Clean tag: `1.0.0`
- Development: `1.0.1.dev5+gd128f6a` (5 commits after v1.0.0)
- Dirty: `1.0.1.dev5+gd128f6a.d20251227` (with uncommitted changes)

## CI/CD Integration

No special configuration needed! Just build normally:

```yaml
# GitHub Actions example
- name: Build API image
  run: docker compose build api

# That's it - version is automatic!
```0.0.0+unknown"

- **Cause**: No git tags in the repository
- **Solution**: Create your first tag: `git tag v0.1.0`

### Version shows "dev-unknown"

- **Cause**: Package not installed (running without Docker)
- **Solution**: This is expected in development. Build with Docker to get proper version.

### "No module named 'setuptools_scm'"

- **Cause**: Missing build dependency
- **Solution**: `pip install setuptools-scm` or rebuild Docker image

### Git mount fails in Docker

- **Cause**: .git directory not accessible or BuildKit not enabled
- **Solution**: Ensure Docker BuildKit is enabled: `export DOCKER_BUILDKIT=1
### Cannot access version endpoint

- **Cause**: API service not running or network issue
- **Solution**: Check API health with `curl http://localhost:8000/health`
