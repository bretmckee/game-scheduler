# Multi-stage build for Celery Scheduler Service
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user
RUN addgroup --system appgroup && \
    adduser --system --group appuser && \
    chown -R appuser:appgroup /app

# Dependencies stage
FROM base AS deps

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv for dependency management
RUN pip install uv

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM base AS production

# Copy installed dependencies from deps stage
COPY --from=deps /app/.venv /app/.venv

# Copy application code
COPY src/shared /app/src/shared
COPY src/scheduler /app/src/scheduler

# Set proper permissions
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Health check for Celery worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD celery -A src.scheduler.celery_app inspect ping || exit 1

# Start Celery worker by default
CMD ["celery", "-A", "src.scheduler.celery_app", "worker", "--loglevel=info", "--concurrency=2"]