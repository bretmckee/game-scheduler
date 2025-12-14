FROM python:3.13-slim

# Install system dependencies
# Note: gcc is needed for building psycopg2 from source
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (alembic, database drivers, messaging, observability)
RUN uv pip install --system -e .

# Copy application files
COPY shared/ ./shared/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY services/init/ ./services/init/

ENTRYPOINT ["python3", "-u", "-m", "services.init.main"]
