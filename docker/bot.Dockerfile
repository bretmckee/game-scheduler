# Multi-stage build for Discord Bot Service
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./
COPY requirements.txt ./
COPY services/bot/requirements.txt ./bot_requirements.txt

# Install Python dependencies
RUN uv pip install --system -r requirements.txt
RUN uv pip install --system -r bot_requirements.txt

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY shared/ ./shared/
COPY services/bot/ ./services/bot/

# Install shared package in editable mode
USER root
RUN pip install -e ./shared
USER appuser

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "-m", "services.bot.main"]
