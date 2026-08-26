#!/usr/bin/env bash
# Creates one Postgres database per name in $POSTGRES_MULTIPLE_DATABASES
# (comma-separated) on first container start, then enables pgvector on
# control_plane (our own knowledge-chunk embeddings — see the plan's
# architecture-pivot note on why this stays local instead of Dograh's
# MPS-backed knowledge base). Two logical databases on one Postgres
# container keeps the single-VPS footprint small: control-plane owns
# tenant data, Dograh owns its own internal schema.
set -euo pipefail

if [ -z "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
  exit 0
fi

IFS=',' read -ra DBS <<< "$POSTGRES_MULTIPLE_DATABASES"
for db in "${DBS[@]}"; do
  echo "Creating database '$db'"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE $db;
EOSQL
done

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname control_plane <<-EOSQL
  CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
