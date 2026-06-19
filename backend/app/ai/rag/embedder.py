"""
Local embedder using fastembed — no API key, no cost, runs on CPU.

Model: BAAI/bge-small-en-v1.5
  - 130MB download (once, cached at ~/.cache/fastembed/)
  - 384-dimensional vectors
  - Excellent at code + English mixed content
  - ~0.5s per 100 chunks on M4 CPU

Usage:
    embedder = Embedder()
    vectors = embedder.embed(["def foo():", "class Bar:"])
    # → list of numpy arrays, shape (384,)
"""
from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_DIM = 384


class Embedder:
    """Lazy-loaded fastembed wrapper — model loads on first use."""

    _instance: "Embedder | None" = None
    _model = None

    def __new__(cls) -> "Embedder":
        # Singleton — only one model loaded across the worker process
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load(self) -> None:
        if self._model is None:
            logger.info(f"[embedder] loading {MODEL_NAME} (first use — downloads if not cached)")
            from fastembed import TextEmbedding
            self._model = TextEmbedding(MODEL_NAME)
            logger.info("[embedder] model ready")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings. Returns list of 384-dim float vectors."""
        if not texts:
            return []
        self._load()
        vectors = list(self._model.embed(texts))
        return [v.tolist() for v in vectors]

    def embed_one(self, text: str) -> list[float]:
        """Convenience method for a single string."""
        return self.embed([text])[0]


# Module-level singleton
embedder = Embedder()
