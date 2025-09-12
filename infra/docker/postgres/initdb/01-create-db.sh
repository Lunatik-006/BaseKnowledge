#!/usr/bin/env bash
set -euo pipefail

# This script is executed by the official Postgres image on the FIRST init
# only (when the data directory is empty). It ensures the database named in
# POSTGRES_DB exists. If POSTGRES_DB=postgres, creation is skipped.

DB_NAME=${POSTGRES_DB:-baseknowledge}
DB_USER=${POSTGRES_USER:-postgres}

if [ "${DB_NAME}" = "postgres" ]; then
  echo "[initdb] POSTGRES_DB is 'postgres' — nothing to create."
  exit 0
fi

echo "[initdb] Ensuring database '${DB_NAME}' exists..."
EXISTS=$(psql -U "${DB_USER}" -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || echo "")
if [ "${EXISTS}" != "1" ]; then
  psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${DB_NAME}\";"
  echo "[initdb] Database '${DB_NAME}' created."
else
  echo "[initdb] Database '${DB_NAME}' already exists."
fi

