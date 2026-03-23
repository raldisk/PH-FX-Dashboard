#!/usr/bin/env bash
# Docker entrypoint — waits for PostgreSQL then dispatches the CLI command.
set -euo pipefail

PG_HOST="${PH_FX_PG_HOST:-postgres}"
PG_PORT="${PH_FX_PG_PORT:-5432}"
MAX_WAIT=60
ELAPSED=0

echo "Waiting for PostgreSQL at ${PG_HOST}:${PG_PORT}..."
until pg_isready -h "$PG_HOST" -p "$PG_PORT" -q; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo "PostgreSQL not ready after ${MAX_WAIT}s — exiting."
        exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done
echo "PostgreSQL is ready."

exec python -m ph_fx.pipeline "$@"
