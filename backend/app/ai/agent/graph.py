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
from collections.abc import Callable
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


_NODE_MESSAGES: dict[str, str] = {
    "fetch":   "Fetching code samples",
    "analyse": "Analyzing code patterns",
    "persona": "Generating developer persona",
    "score":   "Computing skill scores",
}


def run_analysis(
    username: str,
    developer_id: int,
    repos: list[dict],
    github_token: str,
    groq_api_key: str,
    publish: Callable[[dict], None] | None = None,
) -> tuple[str | None, dict | None]:
    """
    Entry point called by the Celery task.
    Returns (ai_persona, skill_scores) — both may be None on failure.

    publish: optional callable that receives progress dicts
             { type: "agent_started"|"agent_step"|"agent_done"|"agent_error", ... }
    """
    _pub = publish or (lambda _: None)

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
    _pub({"type": "agent_started", "message": f"Analyzing @{username}…"})

    try:
        # stream(mode="updates") yields {node_name: {changed_keys}} after each node.
        # We accumulate to reconstruct final state without a second .invoke() call.
        state: dict = dict(initial)
        for node_updates in analysis_graph.stream(initial, stream_mode="updates"):
            for node_name, updates in node_updates.items():
                state.update(updates)
                msg = _NODE_MESSAGES.get(node_name, node_name)
                if node_name == "fetch" and "code_samples" in updates:
                    n = len(updates["code_samples"])
                    msg = f"Fetched {n} code sample{'s' if n != 1 else ''}"
                _pub({"type": "agent_step", "step": node_name, "message": msg})
                logger.debug(f"[analysis_agent] node={node_name} msg={msg}")

        persona = state.get("ai_persona")
        scores = state.get("skill_scores")
        logger.info(
            f"[analysis_agent] done for @{username}: "
            f"persona={'yes' if persona else 'no'}, scores={scores}"
        )
        _pub({"type": "agent_done", "message": "AI analysis complete"})
        return persona, scores

    except Exception:
        logger.exception(f"[analysis_agent] failed for @{username}")
        _pub({"type": "agent_error", "message": "AI analysis failed — profile still usable"})
        return None, None
