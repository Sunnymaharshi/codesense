"""
LLMCall model — tracks every Anthropic API call for cost + observability.
Populated by the RAG streamer and LangGraph agent in Phase 3+.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Which endpoint triggered this call
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)  # /query, /agent, etc.

    # Model info
    model: Mapped[str] = mapped_column(String(100), nullable=False)  # claude-sonnet-4-6

    # Token usage
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)

    # Cost in USD (calculated from token counts + model pricing)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Latency
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    # LangSmith trace URL for debugging
    langsmith_run_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Developer context (optional — helps filter cost per profile)
    github_username: Mapped[Optional[str]] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<LLMCall {self.model} ${self.cost_usd:.4f} [{self.endpoint}]>"
