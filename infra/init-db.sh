#!/bin/sh
# Runs once, on first boot of an empty Postgres volume.
#
# Creates the databases Temporal needs alongside our own, and installs pgvector
# into `sro`. The extension is not used in v0 -- skills carry no embeddings yet --
# but installing it here means the later semantic-lookup work is a migration,
# not an infrastructure change.
set -eu

# Nango gets its own role owning only its own database, not the superuser.
psql -v ON_ERROR_STOP=1 -v nu="$NANGO_DB_USER" -v np="$NANGO_DB_PASSWORD" \
    --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'SQL'
    CREATE DATABASE temporal;
    CREATE DATABASE temporal_visibility;
    CREATE ROLE :"nu" LOGIN PASSWORD :'np';
    CREATE DATABASE nango OWNER :"nu";
    CREATE EXTENSION IF NOT EXISTS vector;
SQL
