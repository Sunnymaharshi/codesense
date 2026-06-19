"""
LangGraph agent — orchestrates retrieve → generate → stream.

State machine:
  START → retrieve_context → generate_response → END

The generate node streams the Groq response token-by-token via an async generator,
which the SSE endpoint consumes and forwards to the client.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, TypedDict

from openai import AsyncOpenAI

from ..rag.retriever import RetrievedChunk, format_context, retrieve
from ..schemas.output import AIMessage
from .prompts import SYSTEM_PROMPT, build_developer_context

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
TEMPERATURE = 0.3  # low — we want consistent structured output


class AgentState(TypedDict):
    question: str
    developer_id: str
    developer: dict
    repos: list[dict]
    stats: dict
    chunks: list[RetrievedChunk]
    response: AIMessage | None


async def run_agent(
    question: str,
    developer: dict,
    repos: list[dict],
    stats: dict,
    groq_api_key: str,
    db,  # AsyncSession — passed in from FastAPI
) -> AsyncGenerator[dict, None]:
    """
    Main entry point. Yields SSE-ready event dicts:
      {"event": "thinking_step", "data": {...}}
      {"event": "token",         "data": {...}}
      {"event": "component",     "data": {...}}
      {"event": "done",          "data": {}}
    """
    developer_id = str(developer["id"])

    # ── Step 1: retrieve ────────────────────────────────────────────────────
    yield {
        "event": "thinking_step",
        "data": {"message": "Searching code across repositories…", "done": False},
    }

    chunks = await retrieve(question, developer_id, db)

    yield {
        "event": "thinking_step",
        "data": {
            "message": f"Found {len(chunks)} relevant code chunks",
            "done": True,
        },
    }

    # ── Step 2: build prompt ─────────────────────────────────────────────────
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

    # ── Step 3: stream from Groq ─────────────────────────────────────────────
    client = AsyncOpenAI(api_key=groq_api_key, base_url=GROQ_BASE_URL)

    full_text = ""
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
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                # Stream each character for the typing effect
                for char in delta:
                    yield {"event": "token", "data": {"char": char}}

    except Exception as exc:
        logger.exception(f"[agent] Groq streaming error: {exc}")
        yield {"event": "error", "data": {"message": str(exc)}}
        return

    yield {"event": "thinking_step", "data": {"message": "Generating insight…", "done": True}}

    # ── Step 4: parse structured output ─────────────────────────────────────
    try:
        # Strip markdown fences if the model added them despite instructions
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
        logger.warning(f"[agent] JSON parse failed, falling back to text: {exc}")
        yield {
            "event": "component",
            "data": {
                "type": "text",
                "text": full_text,
                "data": {},
            },
        }

    yield {"event": "done", "data": {}}
