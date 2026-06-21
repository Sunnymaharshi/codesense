"""
pgvector retriever — cosine similarity search over code chunks.

Requires:
  - code_chunks table with embedding column of type vector(384)
  - Migration 002_vector_column.py must have run
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..rag.embedder import embedder

logger = logging.getLogger(__name__)

TOP_K = 8  # chunks to retrieve per query
MIN_SCORE = 0.15  # natural-language→code cosine similarity is low; 0.3 filters too aggressively


@dataclass
class RetrievedChunk:
    chunk_id: str
    repo_name: str
    file_path: str
    content: str
    language: str
    score: float


async def retrieve(
    query: str,
    developer_id: str,
    db: AsyncSession,
    top_k: int = TOP_K,
) -> list[RetrievedChunk]:
    """
    Embed the query and find the most similar code chunks
    for a specific developer via pgvector cosine similarity.
    """
    query_vector = embedder.embed_one(query)
    vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"

    sql = text("""
        SELECT
            cc.id,
            r.name AS repo_name,
            cc.file_path,
            cc.content,
            cc.language,
            1 - (cc.embedding <=> CAST(:query_vector AS vector)) AS score
        FROM code_chunks cc
        JOIN repos r ON r.id = cc.repo_id
        WHERE r.developer_id = :developer_id
          AND cc.embedding IS NOT NULL
          AND 1 - (cc.embedding <=> CAST(:query_vector AS vector)) > :min_score
        ORDER BY cc.embedding <=> CAST(:query_vector AS vector)
        LIMIT :top_k
    """)

    result = await db.execute(
        sql,
        {
            "query_vector": vector_str,
            "developer_id": int(developer_id),
            "min_score": MIN_SCORE,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    logger.info(f"[retriever] query='{query[:60]}' → {len(rows)} chunks retrieved")

    return [
        RetrievedChunk(
            chunk_id=str(row.id),
            repo_name=row.repo_name,
            file_path=row.file_path,
            content=row.content,
            language=row.language or "text",
            score=float(row.score),
        )
        for row in rows
    ]


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a prompt context block."""
    if not chunks:
        return "No relevant code chunks found."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] {chunk.repo_name}/{chunk.file_path} "
            f"(similarity: {chunk.score:.2f})\n"
            f"```{chunk.language.lower()}\n{chunk.content}\n```"
        )
    return "\n\n".join(parts)
