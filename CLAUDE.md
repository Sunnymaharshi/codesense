# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project

**codesense** — Enter a GitHub username → AI indexes all public repos → renders an interactive developer profile with a RAG-powered chat assistant that streams dynamic React components based on what you ask.

---

## Commands

```bash
# First time only
make setup        # cp .env.example .env + npm install frontend deps

# Daily workflow
make dev          # docker-compose up with hot reload (postgres + redis + api + worker)
make migrate      # alembic upgrade head (run once after first `make dev`)
make frontend     # start Vite dev server in a second terminal

# Utilities
make restart-worker   # restart Celery worker without touching other services
make fresh            # wipe all volumes and start from scratch
make seed             # seed 3 real GitHub profiles
make install          # uv sync locally (for IDE support outside Docker)
make lock             # uv lock (after editing pyproject.toml)
make lint             # ruff check
make format           # ruff format
make test             # pytest (uses in-memory SQLite via aiosqlite — no Postgres needed)
```

Run a single test:
```bash
cd backend && uv run pytest tests/test_health_score.py::test_name -v
```

---

## Architecture

### Directory layout

```
backend/
  app/
    ai/               # all AI code — zero FastAPI knowledge, importable standalone
      rag/            # Phase 3 straight-line pipeline (retrieve → prompt → stream → parse)
        chunker.py    # splits files by function/class boundary, sliding-window fallback
        embedder.py   # fastembed singleton, lazy-loads BAAI/bge-small-en-v1.5 on first use
        retriever.py  # pgvector cosine search, top-k=8, min score 0.3
        pipeline.py   # run_pipeline() — async generator yielding SSE events, called by query.py
        prompts.py    # SYSTEM_PROMPT + build_developer_context() (injects pre-computed ai_persona/skill_scores)
      agent/          # Phase 4 LangGraph agent — runs ONCE during indexing, NOT per chat question
        tools.py      # fetch_code_samples(), analyse_patterns(), compute_growth() — pure Python, no LLM
        nodes.py      # 4 sync node functions: fetch_node, analyse_node, persona_node, score_node
        graph.py      # StateGraph with conditional re-fetch edge; run_analysis() → (ai_persona, skill_scores)
      schemas/
        output.py     # AIMessage pydantic model + per-component data shapes
    api/routes/       # analyze.py, profile.py, query.py, ws.py, compare.py, snapshot.py, agent_trace.py
    workers/          # index_repo.py (fan-out), embed_repo.py, analysis_agent.py, redis_client.py, celery_app.py
    models/           # Developer, Repo, CodeChunk, IndexingJob, ProfileSnapshot, LLMCall
    services/         # github.py (async), github_sync.py (sync, for workers)
    db/               # session.py (async), sync_session.py (for workers)
  migrations/versions/
    001_initial.py              # all 6 tables + pgvector extension
    002_vector_column.py        # ALTER code_chunks.embedding → vector(384) + ivfflat index
    003_add_dev_commit_analytics_fields.py
frontend/src/
  pages/              # Home.tsx, Profile.tsx, Compare.tsx
  components/
    profile/          # ProfileHeader, StatsRow, LanguageBars, RepoCard, RepoGrid, ContributionStats, IndexingProgress, CompareEntry, SnapshotInfo
    compare/          # ComparisonHeader, ComparisonStats
    chat/             # ChatPanel, ThinkingSteps, MessageStream, AskAIButton
    ai-components/    # CommitHeatmap, SkillRadar, GrowthTimeline, RepoComparison, DeveloperPersona, HireRecommendation, TextMessage
    ui/               # Badge, Skeleton, Card
  lib/
    registry.ts       # ComponentType → React.lazy component map
    types.ts          # TypeScript types mirroring backend schemas exactly
    api.ts            # typed fetch wrappers
    api_compare_addition.ts  # compareProfiles(), takeSnapshot(), listSnapshots(), reindexUser()
  store/              # profileStore.ts (Zustand), chatStore.ts (Zustand)
  hooks/              # useIndexingProgress.ts, useChat.ts, useProfileMeta.ts
  styles/             # tokens.css (design tokens), global.css (reset + base only)
```

### Request flows

**Indexing (async):**
```
POST /api/analyze
  → FastAPI upserts Developer, creates IndexingJob, enqueues index_developer.delay()
  → Celery: GitHub API fetches all repos
  → celery.group — one index_single_repo task per repo, all parallel
  → each repo: compute health score → save Repo → trigger embed_repo task
  → embed_repo: fetch files → chunk → fastembed → upsert code_chunks (pgvector)
  → on_indexing_complete chord: auto-snapshot → Redis PUBLISH progress
  → WS /ws/{username} subscribes to pub/sub → streams events to frontend
```

**RAG query (SSE):**
```
POST /api/query
  → embed question locally (fastembed) → pgvector cosine search, top-k=8
  → build prompt: system prompt + retrieved chunks + developer context stats
  → Groq llama-3.3-70b stream via OpenAI-compatible API
  → yield SSE: thinking_step events → token events → component_type/data events → done
```

### SSE event protocol

```
event: thinking_step   data: { "message": "Retrieving commits…", "done": false|true }
event: token           data: { "char": "R" }
event: component_type  data: { "type": "commit_heatmap" }
event: component_data  data: { ...partial payload... }
event: done            data: {}
```

Frontend parses via `fetch()` + `ReadableStream` — NOT `EventSource` (EventSource can't send a POST body).

### AI component registry

`src/lib/registry.ts` maps `ComponentType → React.lazy(component)`. The LLM returns `{ type, text, data }` JSON. The frontend looks up `type` and renders the component inline in chat. To add a new component type:
1. Add the type literal to `AIMessage` in `backend/app/ai/schemas/output.py`
2. Build the React component in `frontend/src/components/ai-components/`
3. Register it in `frontend/src/lib/registry.ts`

Component types: `commit_heatmap`, `skill_radar`, `growth_timeline`, `code_pattern`, `repo_comparison`, `developer_persona`, `hire_recommendation`, `text`

### Database

```
Developer  → Repo (one-to-many, via developer_id FK)
Developer  → IndexingJob (one-to-many)
Developer  → ProfileSnapshot (one-to-many)
Repo       → CodeChunk (one-to-many; embedding is vector(384) after migration 002)
LLMCall    → standalone cost-tracking table (columns exist, nothing writes to it yet)
```

`Developer.ai_persona` and `Developer.skill_scores` (jsonb) have existed since migration 001 and remain empty — Phase 4 (LangGraph agent) will populate them.

---

## Non-obvious rules

**WebSocket CORS:** `CORSMiddleware` does not cover WebSocket upgrades. `app/api/routes/ws.py` manually reads `websocket.headers.get("origin")` and validates it against `settings.CORS_ORIGINS` before calling `.accept()`. `.env` must have `CORS_ORIGINS=http://localhost:5173` with no trailing slash.

**Workers must use sync:** Celery tasks cannot use async SQLAlchemy or httpx. Use `app/db/sync_session.py` (`SyncSessionLocal`) and `app/services/github_sync.py` inside any worker task.

**SQLAlchemy columns never conditional:** Do not write `if X: col = Column(...)` inside a model class body — it breaks declarative mapping. Always define columns unconditionally; use `Text` as a placeholder and ALTER in a migration.

**`query.py` stats are local:** `app/api/routes/query.py` has its own `_build_stats(repos)` helper — it does NOT import from `profile.py`. The field names differ between the two routes.

**`ai/rag/` vs `ai/agent/`:** `ai/rag/pipeline.py` is the Phase 3 per-question RAG pipeline (async, called by `query.py`). `ai/agent/graph.py` is the Phase 4 analysis agent (sync, called by `analysis_agent.py` Celery task). The agent runs once per developer during indexing; the pipeline runs on every chat question. Do not mix them up.

**Celery task registration:** Both `app.workers.index_repo` and `app.workers.analysis_agent` must be listed in `celery_app.py`'s `include` list. Missing either means the worker silently drops tasks with `KeyError: unregistered task`.

**Re-index WebSocket reconnect:** `useIndexingProgress` only opens a WebSocket when `[username, wsSession]` changes. Re-indexing the same profile (same username) increments `wsSession` in the Zustand store (`incrementWsSession()`) to force a new WS connection. `setUsername` also resets all indexing state when switching between profiles so stale `"running"` status from a previous profile never bleeds into the next.

**In-progress guard on `/api/analyze`:** If `developer.index_status` is `pending` or `running`, the endpoint returns early (even with `?force=true`) rather than spawning a duplicate Celery fan-out.

---

## CSS conventions

Every component has its own `.module.css`. No global utility classes, no Tailwind. Import as `import styles from "./Foo.module.css"`. Design tokens (colors, spacing, typography) live in `src/styles/tokens.css` as CSS custom properties. `src/styles/global.css` only imports tokens, CSS reset, and base body styles — nothing else goes there.

SVG charts are built by hand (d3 for math, React renders the SVG). No Recharts or Chart.js.

---

## Stack decisions (locked — don't revisit)

| Decision | Reason |
|----------|--------|
| FastAPI + React/Vite, not Next.js | FastAPI is the backend. No SSR needed. |
| CSS Modules + Radix UI, not Tailwind | Full design control, scoped styles, Radix for accessibility. |
| `uv` not pip | 10–100x faster, `pyproject.toml` + `uv.lock`. Never use pip or requirements.txt. |
| `fastembed` not OpenAI for embeddings | Free, local, no API key, M4 CPU friendly. Model: `BAAI/bge-small-en-v1.5` (384-dim, ~130MB cached). |
| Groq not Anthropic/OpenAI for generation | Free tier (14.4k req/day), OpenAI-compatible API, LPU is ~10x faster. Model: `llama-3.3-70b-versatile`. |
| pgvector not Pinecone | Keep everything in Postgres, no extra service. |
| `ai/` inside `backend/app/` | Importable by workers and routes without circular imports. |

---

## Environment variables

```bash
GITHUB_TOKEN=                # public_repo scope only, 5000 req/hr free
SECRET_KEY=                  # python -c "import secrets; print(secrets.token_hex(32))"
DATABASE_URL=postgresql+asyncpg://codesense:codesense@postgres:5432/codesense
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173    # no trailing slash — WS origin check uses this
GROQ_API_KEY=                # console.groq.com, free, no credit card
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=codesense
# Production only:
SENTRY_DSN_BACKEND=
SENTRY_DSN_FRONTEND=
```

---

## API endpoints (current)

```
POST /api/analyze                           # submit username → start indexing (skips if indexed < 1hr; ?force=true to bypass; 409 if already in progress)
GET  /api/profile/{username}                # full profile data
GET  /api/profile/{username}/agent-trace    # has_analysis, skill_scores, ai_persona, optional LangSmith trace URL
GET  /api/compare/{user1}/{user2}           # side-by-side profiles as { left, right }
POST /api/snapshot/{username}               # save a profile snapshot
GET  /api/snapshots/{username}              # list saved snapshots
POST /api/query                             # RAG question → SSE stream
WS   /ws/{username}                         # live indexing progress
```
