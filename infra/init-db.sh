#!/bin/sh
# Runs once, on first boot of an empty Postgres volume.
#
# Creates the databases Temporal needs alongside our own, and installs pgvector
# into `sro`. The extension is not used in v0 -- skills carry no embeddings yet --
# but installing it here means the later semantic-lookup work is a migration,
# not an infrastructure change.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'SQL'
    CREATE DATABASE temporal;
    CREATE DATABASE temporal_visibility;
    CREATE EXTENSION IF NOT EXISTS vector;
SQL
