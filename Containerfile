# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

# Install uv for high-speed dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install system dependencies for PostGIS/Psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (for caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install runtime spatial libraries for PostGIS/GDAL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN mkdir -p /app/docs/research && chown -R appuser:appgroup /app

# Copy the virtual environment from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Set environment paths
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY --chown=appuser:appgroup . .

USER appuser

# Expose FastAPI port
EXPOSE 8000

# Metadata for Agent Memory Protocol
LABEL maintainer="Legacy Mentor"
LABEL version="1.0"
LABEL protocol="Agent Memory Protocol v1.0"

# Default command matches your 'just start' intent
CMD ["fastapi", "run", "main.py", "--port", "8000"]