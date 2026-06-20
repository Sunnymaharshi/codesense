"""
Phase 3 RAG pipeline — retrieve → prompt → stream → parse.

This is the per-question pipeline used by POST /api/query.
NOT the Phase 4 analysis agent (that is ai/agent/graph.py).

Moved here from ai/agent/graph.py to free that path for the real LangGraph agent.
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

from openai import AsyncOpenAI

from ..rag.retriever import RetrievedChunk, format_context, retrieve
from ..schemas.output import AIMessage
from .prompts import SYSTEM_PROMPT, build_developer_context

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
TEMPERATURE = 0.3

# Groq llama-3.3-70b-versatile pricing (USD per token)
_COST_IN = 0.59 / 1_000_000
_COST_OUT = 0.79 / 1_000_000


async def run_pipeline(
    question: str,
    developer: dict,
    repos: list[dict],
    stats: dict,
    groq_api_key: str,
    db,
) -> AsyncGenerator[dict, None]:
    """
    Yields SSE-ready event dicts:
      {"event": "thinking_step", "data": {...}}
      {"event": "token",         "data": {...}}
      {"event": "component",     "data": {...}}
      {"event": "done",          "data": {}}
    """
    developer_id = str(developer["id"])

    yield {
        "event": "thinking_step",
        "data": {"message": "Searching code across repositories…", "done": False},
    }

    chunks = await retrieve(question, developer_id, db)

    yield {
        "event": "thinking_step",
        "data": {"message": f"Found {len(chunks)} relevant code chunks", "done": True},
    }

    yield {
        "event": "thinking_step",
        "data": {"message": "Analysing developer profile…", "done": False},
    }

    developer_context = build_developer_context(developer, repos, stats)
    code_context = format_context(chunks)

    system = SYSTEM_PROMPT.format(
        developer_context=developer_context,
        code_context=code_context,
    )

    yield {
        "event": "thinking_step",
        "data": {"message": "Analysing developer profile…", "done": True},
    }
    yield {"event": "thinking_step", "data": {"message": "Generating insight…", "done": False}}

    client = AsyncOpenAI(api_key=groq_api_key, base_url=GROQ_BASE_URL)

    full_text = ""
    usage = None
    start_ms = int(time.monotonic() * 1000)

    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.usage:
                usage = chunk.usage
            if chunk.choices:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_text += delta
                    for char in delta:
                        yield {"event": "token", "data": {"char": char}}

    except Exception as exc:
        logger.exception(f"[pipeline] Groq streaming error: {exc}")
        yield {"event": "error", "data": {"message": str(exc)}}
        return

    duration_ms = int(time.monotonic() * 1000) - start_ms

    # Log cost to LLMCall table — fire and forget, never fails the stream
    try:
        from app.models.llm_call import LLMCall

        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        llm_call = LLMCall(
            endpoint="/query",
            model=MODEL,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(tokens_in * _COST_IN + tokens_out * _COST_OUT, 8),
            duration_ms=duration_ms,
            github_username=developer.get("github_username"),
        )
        db.add(llm_call)
        await db.commit()
    except Exception:
        logger.warning("[pipeline] failed to log LLMCall", exc_info=True)

    yield {"event": "thinking_step", "data": {"message": "Generating insight…", "done": True}}

    try:
        clean = full_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        if clean.endswith("```"):
            clean = clean[:-3]

        parsed = json.loads(clean.strip())
        message = AIMessage(**parsed)
        yield {"event": "component", "data": message.model_dump()}

    except Exception as exc:
        logger.warning(f"[pipeline] JSON parse failed, falling back to text: {exc}")
        yield {"event": "component", "data": {"type": "text", "text": full_text, "data": {}}}

    yield {"event": "done", "data": {}}
