"""
Phase 4 — LangGraph analysis agent.

Runs ONCE during indexing (triggered from Celery on_indexing_complete).
NOT the per-question RAG pipeline — that lives in ai/rag/pipeline.py.

Flow:
  START → fetch
  fetch → [conditional] → if data sufficient OR 2nd attempt → analyse
                        → if sparse AND 1st attempt          → fetch (retry)
  analyse → persona → score → END
"""

from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .nodes import analyse_node, fetch_node, persona_node, score_node

logger = logging.getLogger(__name__)


class AnalysisState(TypedDict):
    username: str
    developer_id: int
    github_token: str
    groq_api_key: str
    repos: list[dict]
    code_samples: list[dict]
    analysis: dict
    growth: list[dict]
    ai_persona: str | None
    skill_scores: dict | None
    fetch_attempts: int
    is_data_sufficient: bool


def _route_after_fetch(state: AnalysisState) -> str:
    if state["is_data_sufficient"] or state["fetch_attempts"] >= 2:
        return "analyse"
    return "fetch"


def _build_graph() -> StateGraph:
    builder = StateGraph(AnalysisState)

    builder.add_node("fetch", fetch_node)
    builder.add_node("analyse", analyse_node)
    builder.add_node("persona", persona_node)
    builder.add_node("score", score_node)

    builder.add_edge(START, "fetch")
    builder.add_conditional_edges(
        "fetch",
        _route_after_fetch,
        {"fetch": "fetch", "analyse": "analyse"},
    )
    builder.add_edge("analyse", "persona")
    builder.add_edge("persona", "score")
    builder.add_edge("score", END)

    return builder.compile()


# Compiled once at import time — reused across all Celery task invocations
analysis_graph = _build_graph()


def run_analysis(
    username: str,
    developer_id: int,
    repos: list[dict],
    github_token: str,
    groq_api_key: str,
) -> tuple[str | None, dict | None]:
    """
    Entry point called by the Celery task.
    Returns (ai_persona, skill_scores).
    Both may be None if the agent fails — caller handles gracefully.
    """
    initial: AnalysisState = {
        "username": username,
        "developer_id": developer_id,
        "github_token": github_token,
        "groq_api_key": groq_api_key,
        "repos": repos,
        "code_samples": [],
        "analysis": {},
        "growth": [],
        "ai_persona": None,
        "skill_scores": None,
        "fetch_attempts": 0,
        "is_data_sufficient": False,
    }

    logger.info(f"[analysis_agent] starting for @{username} ({len(repos)} repos)")
    try:
        result = analysis_graph.invoke(initial)
        persona = result.get("ai_persona")
        scores = result.get("skill_scores")
        logger.info(
            f"[analysis_agent] done for @{username}: "
            f"persona={'yes' if persona else 'no'}, scores={scores}"
        )
        return persona, scores
    except Exception:
        logger.exception(f"[analysis_agent] failed for @{username}")
        return None, None
