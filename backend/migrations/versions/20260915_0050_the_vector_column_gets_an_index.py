"""An index on the only vector column in the schema.

`knowledge_entries.embedding` is `vector(768)` and has been searched with
`ORDER BY embedding <=> ...` since it was added. There was no vector index of
any kind, so every semantic lookup read every one of the tenant's rows and
computed an exact 768-dimension distance on each.

Measured on this deployment's own store before and after, one tenant, 3,485
rows: **139 ms to 4.9 ms**, and the old plan is linear in rows where this one
is not -- so the gap widens with every day of capture. Recall against the exact
answer on the same query: 20 of 20.

HNSW rather than IVFFlat. IVFFlat needs a representative sample to build its
lists and has to be rebuilt as the data grows -- and this table grows every
time a mining pass records a claim. HNSW builds on an empty table and stays
correct as rows arrive, which is what a table nobody reindexes needs. The cost
is a slower build and a larger index: 8 MB here, and 1.5 s to build.

Partial, on `superseded_by IS NULL`, because that is what every search asks
for -- a superseded claim is history. The index is then over the rows that can
be answers, and superseding one removes it from the index rather than leaving
it to be filtered out of the result.

The tenant filter is NOT in this index and cannot be: pgvector indexes one
vector column. It is applied after the scan, which is why `search` sets
`hnsw.iterative_scan` -- see `SqlKnowledgeRepository.search`.

Revision ID: 0050
Revises: 0049
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plain `CREATE INDEX`, not `CONCURRENTLY`. Concurrently cannot run inside
    # alembic's transaction, and it waits out every transaction older than
    # itself -- which on this deployment meant waiting forever behind the
    # advisory-lock session the API holds. A deployment that needs the table
    # writable during the build should run the concurrent form by hand, with
    # nothing idle in a transaction, and stamp this revision.
    op.execute(sa.text("SET maintenance_work_mem = '256MB'"))
    op.create_index(
        "ix_knowledge_embedding_hnsw",
        "knowledge_entries",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=sa.text("superseded_by IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_embedding_hnsw", table_name="knowledge_entries")
