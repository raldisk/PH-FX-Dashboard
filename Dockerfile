# Multi-stage Dockerfile
# Stage 1: builder — install dependencies
# Stage 2: runtime — lean production image

FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim AS runtime

# Install pg_isready (used by entrypoint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source
COPY src/     ./src/
COPY transforms/ ./transforms/
COPY scripts/ ./scripts/
COPY dashboard/ ./dashboard/
COPY pyproject.toml .

# Install package in editable mode
RUN pip install --no-cache-dir -e . --no-deps

# Non-root user
RUN useradd -m -u 1000 appuser
RUN chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["bash", "scripts/entrypoint.sh"]
CMD ["ingest"]
