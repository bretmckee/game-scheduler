# Multi-stage build for FastAPI Service
FROM python:3.13-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies only (without the package itself)
RUN uv pip install --system .

# Copy source code to match git working directory state
COPY shared/ ./shared/
COPY services/ ./services/

# Final step: install package with version from git
# Convert git describe output to PEP 440 format (v0.0.1-479-ge95e5f2 → 0.0.1.post479+ge95e5f2)
RUN --mount=source=.git,target=.git,type=bind \
    export GIT_VERSION=$(git describe --tags --always) && \
    export PEP440_VERSION=$(echo "$GIT_VERSION" | sed -E 's/^v//; s/-([0-9]+)-g/.post\1+g/') && \
    SETUPTOOLS_SCM_PRETEND_VERSION="$PEP440_VERSION" uv pip install --system --no-deps . && \
    python -c "import importlib.metadata; print(importlib.metadata.version('game-scheduler'), end='')" > /app/.build_version

# Development stage
FROM base AS development

# Set GIT_VERSION environment variable from the captured build version
# This ensures the version is available even when source is volume-mounted
RUN GIT_VERSION=$(cat /app/.build_version) && \
    echo "export GIT_VERSION=${GIT_VERSION}" > /etc/profile.d/git_version.sh
ENV GIT_VERSION="dev-unknown"

# Create non-root user with UID 1000
# Note: Source files must be world-readable for volume mounts to work
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 --gid 1000 appuser

# Set working directory ownership
RUN chown -R appuser:appgroup /app

# Create cache directory with proper permissions
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appgroup /home/appuser/.cache

USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Use uvicorn with reload for development
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM python:3.13-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY shared/ ./shared/
COPY services/api/ ./services/api/

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
