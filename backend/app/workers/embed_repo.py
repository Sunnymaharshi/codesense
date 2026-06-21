"""
Celery task: embed a repo's code files into pgvector.

Triggered after indexing completes.

Flow:
  fetch code files from GitHub API
    → chunker splits by function boundary
    → fastembed embeds each chunk (local, free, 384-dim)
    → upsert into code_chunks table
"""

import logging

from sqlalchemy import delete

from app.ai.rag.chunker import chunk_file
from app.ai.rag.embedder import embedder
from app.db.sync_session import SyncSessionLocal
from app.models.embedding import CodeChunk
from app.models.profile import Repo
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

EMBEDDABLE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".swift",
    ".kt",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
}

SKIP_PATHS = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "coverage",
    ".next",
    "target",
}

MAX_FILE_SIZE = 50_000
MAX_FILES_PER_REPO = 30


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def embed_repo(self, repo_id: str) -> dict:
    """Fetch, chunk, embed, and store code chunks for one repo."""
    logger.info(f"[embed_repo] starting for repo_id={repo_id}")

    with SyncSessionLocal() as db:
        repo = db.get(Repo, repo_id)
        if not repo:
            logger.error(f"[embed_repo] repo {repo_id} not found")
            return {"ok": False, "reason": "not found"}
        repo_name = repo.name
        repo_description = repo.description or ""
        repo_full_name = repo.full_name or repo_name
        owner, name = repo_name.split("/", 1)

    try:
        from app.services.github import GitHubService

        github = GitHubService()
        files = github.get_repo_files_sync(
            owner, name, EMBEDDABLE_EXTENSIONS, SKIP_PATHS, MAX_FILES_PER_REPO
        )
    except Exception as exc:
        logger.exception(f"[embed_repo] failed to fetch files for {repo_name}: {exc}")
        raise self.retry(exc=exc)

    if not files:
        logger.info(f"[embed_repo] no embeddable files in {repo_name}")
        return {"ok": True, "chunks": 0}

    all_chunks = []

    if repo_description:
        from app.ai.rag.chunker import CodeChunk as _Chunk
        desc_text = f"{repo_full_name}: {repo_description}"
        all_chunks.append(_Chunk(
            file_path="description",
            chunk_index=0,
            content=desc_text,
            language="text",
        ))

    for file_path, content, language in files:
        if len(content) > MAX_FILE_SIZE:
            content = content[:MAX_FILE_SIZE]
        chunks = chunk_file(file_path, content, language)
        all_chunks.extend(chunks)

    if not all_chunks:
        return {"ok": True, "chunks": 0}

    texts = [c.content for c in all_chunks]
    vectors = embedder.embed(texts)

    with SyncSessionLocal() as db:
        db.execute(delete(CodeChunk).where(CodeChunk.repo_id == repo_id))
        for chunk, vector in zip(all_chunks, vectors):
            vector_str = "[" + ",".join(str(x) for x in vector) + "]"
            db_chunk = CodeChunk(
                repo_id=repo_id,
                file_path=chunk.file_path,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                language=chunk.language,
                embedding=vector_str,
                token_count=len(chunk.content) // 4,
            )
            db.add(db_chunk)
        db.commit()

    logger.info(f"[embed_repo] {repo_name}: {len(all_chunks)} chunks embedded")
    return {"ok": True, "chunks": len(all_chunks)}
