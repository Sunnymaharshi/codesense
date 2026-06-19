"""002_vector_column

ALTER code_chunks.embedding from TEXT to vector(384).
Must run after Phase 1 migration (001_initial).

Run with: make migrate
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Drop existing text column and recreate as vector(384)
    op.execute("ALTER TABLE code_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE code_chunks ADD COLUMN embedding vector(384)")

    # Index for fast cosine similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_code_chunks_embedding
        ON code_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # Add language column if missing
    op.execute("""
        ALTER TABLE code_chunks
        ADD COLUMN IF NOT EXISTS language VARCHAR(50)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_code_chunks_embedding")
    op.execute("ALTER TABLE code_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE code_chunks ADD COLUMN embedding TEXT")
    op.execute("ALTER TABLE code_chunks DROP COLUMN IF EXISTS language")
