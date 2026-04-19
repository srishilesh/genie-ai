#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h "${PGHOST:-postgres}" -U "${POSTGRES_USER:-genie}" -q; do
  sleep 1
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
