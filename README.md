# codesense

**The complete picture of any developer.**

Enter a GitHub username. codesense indexes every public repository, computes a health score for each one, runs a LangGraph analysis agent to build a developer persona, and gives you an AI assistant that answers questions about the developer by reading their actual code — not just their commit graph.

[**How to explain this**](#how-to-explain-this-project) · [**Architecture**](#architecture) · [**Setup**](#local-setup) · [**Why these choices**](#why-these-technical-choices)

---

## What it does

1. **Index** — paste a GitHub username; codesense fans out across every public repo in parallel (Celery), computing a health score (tests, CI, docs, license, activity) for each one with live WebSocket progress
2. **Profile** — a data-dense profile page: stats row, language breakdown, repo grid sorted by health grade, contribution patterns, snapshot history
3. **Agent analysis** — after indexing, a 4-node LangGraph agent fetches up to 24 source files, analyses code patterns with pure Python regex, then asks Groq to generate a developer persona and skill scores (Backend / Frontend / DevOps / Testing / AI-ML) — stored once, reused everywhere
4. **Ask anything** — a chat panel backed by RAG over the developer's actual source code. Retrieves real code chunks via pgvector cosine similarity, streams a response with token-by-token typing effect and contextual thinking steps
5. **AI decides the UI** — the assistant returns structured JSON `{ type, text, data }`; a frontend component registry maps `type` to a React component and renders it inline — commit heatmap, skill radar, growth timeline, hire recommendation card, or plain text
6. **Compare** — `/compare/:user1/:user2` puts two developers side-by-side with shared stats comparison and a winner highlight on each metric
7. **Snapshots** — profile state is captured automatically after every index run; snapshot history shows how a developer's stack and health scores have changed over time

![chat panel streaming a skill radar component](docs/demo.gif)

---

## Architecture

Three independent pipelines sharing one Postgres database:

```
┌─────────────────────────────────────────────────────────────────┐
│  INDEXING PIPELINE  (async — Celery + Redis + WebSocket)        │
│                                                                 │
│  POST /analyze → IndexingJob → index_developer (Celery)         │
│                                     │                           │
│                          celery.group (one task per repo)        │
│                          ├─ index_single_repo (×N, parallel)    │
│                          │    → GitHub API: languages, commits,  │
│                          │      13 signal checks, health score   │
│                          │    → Postgres: upsert Repo row        │
│                          │    → Redis PUBLISH progress event     │
│                          └─ on_indexing_complete (chord callback)│
│                               → ProfileSnapshot saved           │
│                               → analyse_developer.delay()       │
│                                                                 │
│  WS /ws/:username ◀── Redis pub/sub ◀── progress events        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LANGGRAPH AGENT PIPELINE  (async Celery, runs once per dev)    │
│                                                                 │
│  analyse_developer (Celery task)                                │
│    → LangGraph StateGraph.invoke()                              │
│        ├─ fetch_node: fetch_code_samples() — up to 24 files     │
│        │    (conditional re-fetch if < 5 samples on first try)  │
│        ├─ analyse_node: analyse_patterns() + compute_growth()   │
│        │    (pure Python regex — zero tokens sent to LLM)       │
│        ├─ persona_node: Groq call — ~150 tokens, 2-3 sentences  │
│        └─ score_node: Groq call — JSON {backend,frontend,...}   │
│    → Developer.ai_persona + skill_scores persisted to Postgres  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  RAG QUERY PIPELINE  (sync per-request, SSE streaming)          │
│                                                                 │
│  POST /query → embed question (fastembed, local, 384-dim)       │
│    → pgvector cosine search → top-k CodeChunk rows              │
│    → build prompt: system + chunks + ai_persona + skill_scores  │
│    → Groq llama-3.3-70b streaming completion                    │
│    → parse structured JSON { type, text, data }                 │
│    → SSE events: thinking_step → token → component_type         │
│                  → component_data → done                        │
│    → LLMCall row written (tokens_in, tokens_out, cost_usd)      │
│                                                                 │
│  Frontend: AnimatePresence skeleton → component fill            │
└─────────────────────────────────────────────────────────────────┘
```

---

## How to explain this project

### The one-liner

> "codesense is a GitHub developer profiler with a RAG-powered chat assistant. You give it a username, it indexes every public repo in parallel, runs a LangGraph agent to build a developer persona and skill scores, and then lets you ask questions about the developer — returning structured JSON that the frontend renders as interactive visualisations instead of plain text."

### Is it "multi-agent RAG"?

**Honest answer: no.** Be precise here — interviewers will probe this.

It has **one LangGraph agent** (a 4-node `StateGraph`) and **one RAG pipeline**. These are separate systems that run at different times:

| | LangGraph agent | RAG pipeline |
|---|---|---|
| When it runs | Once, after indexing completes | On every chat question |
| What it does | Fetches code → regex analysis → Groq for persona + scores | Embeds question → pgvector search → Groq for response |
| Output | `ai_persona` + `skill_scores` stored in Postgres | SSE stream → rendered component |
| Token cost | ~400-600 total per developer | ~3,000-6,000 per query |

The agent enriches the context that RAG uses. RAG retrieves relevant code chunks; the agent's pre-computed persona and skill scores give the LLM a richer picture of the developer beyond what's in any single chunk.

"Multi-agent" means multiple agents collaborating or competing — that's not what this is. The safe framing: **"a RAG system with a preprocessing analysis agent."**

---

### Complete flow — what actually happens

#### When a user enters a GitHub username

```
1.  Home page → POST /api/analyze
    FastAPI upserts Developer row, creates IndexingJob, returns {job_id} immediately.
    No blocking — the response is back in ~50ms.

2.  Celery enqueues index_developer(developer_id, job_id).
    Frontend opens WebSocket to /ws/{username} and waits.

3.  index_developer (Celery worker):
    → fetches all public repos from GitHub API (one paginated call)
    → builds celery.group — one index_single_repo task per repo
    → registers on_indexing_complete as the chord callback
    → group dispatches; all repo tasks run in parallel

4.  Each index_single_repo (running concurrently, one per repo):
    → GitHub API: GET /repos/:owner/:repo/languages
    → GitHub API: GET /repos/:owner/:repo/commits?per_page=1 (commit count via header)
    → GitHub API: GET /repos/:owner/:repo/contents (check README, tests, CI, Docker, license)
    → compute_health_score() → A/B/C/D/F grade (13 signals, weighted)
    → upsert Repo row in Postgres
    → redis.publish("codesense:progress:{username}", {repos_done, repos_total})

5.  Redis pub/sub → WebSocket handler → frontend progress bar updates in real time.

6.  on_indexing_complete (chord callback, fires when all repo tasks finish):
    → marks IndexingJob done, updates developer.indexed_at
    → saves ProfileSnapshot (repo stats frozen in time)
    → enqueues analyse_developer.delay(developer_id)
    → redis.publish({type: "done"})

7.  Frontend receives "done" — WebSocket stays open waiting for agent events.

8.  analyse_developer (Celery worker — Phase 4 LangGraph agent):
    → LangGraph StateGraph.stream(stream_mode="updates")

    ├─ fetch_node:
    │    picks top repos by health score and star count (max 8 repos)
    │    fetches 3 source files per repo from GitHub (max 3,000 chars each)
    │    conditional edge: if < 5 samples and first attempt → re-fetch with broader criteria
    │    publishes: {type:"agent_step", step:"fetch", message:"Fetched 12 code samples"}

    ├─ analyse_node (pure Python, zero LLM calls):
    │    type_hint_rate  — regex: count parameters with `: type` annotations
    │    error_handling_rate — count try/except blocks
    │    docstring_rate  — count triple-quote docstrings
    │    test_pattern_rate — count test_ functions and assert statements
    │    compute_growth() — milestones by year from repo push dates
    │    publishes: {type:"agent_step", step:"analyse"}

    ├─ persona_node:
    │    sends aggregated stats (~150 tokens) to Groq
    │    gets back 2-3 sentence developer persona
    │    publishes: {type:"agent_step", step:"persona"}

    └─ score_node:
         sends stats to Groq, gets {backend:75, frontend:60, devops:80, testing:55, ai_ml:40}
         heuristic fallback if Groq call fails (task never hard-fails)
         publishes: {type:"agent_step", step:"score"}

    → saves developer.ai_persona + developer.skill_scores to Postgres
    → publishes: {type:"agent_done"}

9.  Frontend receives "agent_done":
    → WebSocket closes
    → profile refetches → "AI analyzed" badge appears
    → IndexingProgress banner shows "Indexed N repos · AI analyzed" then fades
```

#### When a user asks a question in chat

```
1.  User types question → POST /api/query {username, question}

2.  Rate limit check:
    Redis INCR "codesense:ratelimit:{ip}" with 60s TTL
    > 20 requests/min → 429 Too Many Requests

3.  Load Developer from Postgres (including ai_persona, skill_scores).

4.  Embed the question locally:
    fastembed BAAI/bge-small-en-v1.5 → 384-dim vector
    Runs on CPU inside the FastAPI container — no API call, ~30-50ms.

5.  pgvector cosine search:
    SELECT * FROM code_chunks
    ORDER BY embedding <=> $question_vector
    WHERE 1 - (embedding <=> $question_vector) > 0.3
    LIMIT 8

6.  Build prompt:
    SYSTEM_PROMPT
    + build_developer_context(developer)  ← injects ai_persona + skill_scores
    + top-8 retrieved code chunks (with repo/file context)
    + "Question: {question}"

7.  AsyncOpenAI(base_url="https://api.groq.com/openai/v1")
    .chat.completions.create(model="llama-3.3-70b-versatile", stream=True)

8.  Stream parsing and SSE emission:
    → yield: event:thinking_step  data:{message:"Retrieving relevant code…", done:false}
    → yield: event:thinking_step  data:{message:"Analyzing patterns…", done:true}
    → yield: event:token          data:{char:"T"}  (character by character)
    → ... (full response builds up)
    → final chunk: parse JSON {type, text, data}
    → yield: event:component_type data:{type:"skill_radar"}
    → yield: event:component_data data:{backend:75, frontend:60, ...}
    → yield: event:done           data:{}
    → write LLMCall row (tokens_in, tokens_out, cost_usd, duration_ms)

9.  Frontend reads via fetch() + ReadableStream (NOT EventSource — can't POST with EventSource).
    ThinkingSteps component renders during processing.
    Tokens stream with typing effect via character-by-character state updates.
    On component_type: registry.ts maps type → React.lazy(component)
    On component_data: component renders with live data
```

---

### The AI-decides-UI pattern

This is the most architecturally interesting part and worth explaining clearly.

The LLM doesn't just return text. The system prompt instructs it to return structured JSON:
```json
{ "type": "skill_radar", "text": "Here are their skill scores...", "data": { "backend": 75, "frontend": 60 } }
```

`registry.ts` on the frontend maps `type` → `React.lazy(component)`:
```typescript
const registry = {
  skill_radar:        React.lazy(() => import("../ai-components/SkillRadar")),
  commit_heatmap:     React.lazy(() => import("../ai-components/CommitHeatmap")),
  hire_recommendation: React.lazy(() => import("../ai-components/HireRecommendation")),
  // ...
}
```

The AI decides which component to render based on what the question is asking for. "Show me their skill breakdown" → `skill_radar`. "Should I hire them?" → `hire_recommendation`. "How active are they?" → `commit_heatmap`. The user never picks a chart type — the LLM does.

This is the same pattern Claude.ai uses for artifacts. It separates the intelligence (what to show) from the presentation (how to render it).

---

### Questions interviewers will ask

**"How does the RAG actually work?"**

Retrieval-Augmented Generation: instead of asking the LLM about a developer from its training data (which it doesn't have), we retrieve actual chunks of their code and inject them into the prompt. The LLM reasons over real evidence. The retrieval step is a semantic vector search — the question is embedded into the same 384-dim space as the code chunks, and we return the 8 closest chunks by cosine similarity.

**"What's the difference between the LangGraph agent and the RAG pipeline?"**

The agent runs once at indexing time — it does offline analysis. Pure Python regex computes code quality signals (no LLM involvement), then two small Groq calls generate a persona and skill scores from those signals. These are stored in the database.

The RAG pipeline runs per question at query time — it retrieves relevant chunks and generates a response. The pre-computed persona and skill scores are injected into the RAG prompt as developer context, so the LLM has both specific code evidence (retrieved chunks) and a holistic picture (agent's analysis) when forming an answer.

**"Why run the agent at indexing time and not per query?"**

Cost and latency. Fetching 24 files and running analysis would add 3-5 seconds to every chat response and would re-compute things that don't change between questions. By doing it once, queries stay under 2 seconds and the cost stays near zero per query.

**"How much does this cost to run?"**

Near zero. Embeddings are local (fastembed on CPU — no API cost). Groq has a free tier of 14,400 requests/day. The agent sends ~400-600 tokens total per developer (stats only — raw code never leaves the server). Each RAG query sends ~3,000-6,000 tokens. At Groq's paid rates that's under $0.005 per query.

**"How does it handle hallucination?"**

RAG grounds responses in actual code from the developer's repos. The system prompt instructs the LLM to base its answer only on the retrieved chunks and developer stats, not general knowledge. The LangGraph agent uses pure Python regex for all measurements — there's no LLM involved in the analysis phase, only in the natural language generation step, where it's summarising verified data. Thinking steps are surfaced to the user to make the retrieval process transparent.

**"What would you improve?"**

Three concrete things: (1) Add source metadata (`repo_name`, `file_path`) above each retrieved chunk so the LLM can cite specific files instead of saying "their code." (2) Use a gevent worker pool for Celery — GitHub API calls are IO-bound, so switching from 4 prefork processes to 50 gevent coroutines would cut indexing time by ~8×. (3) Build the `CodePattern` component — `shiki` syntax highlighting is already installed, it just needs wiring to a frontend component and a prompt update.

**"How does the WebSocket work with CORS?"**

`CORSMiddleware` in FastAPI/Starlette only applies to HTTP requests — it doesn't cover WebSocket upgrade requests. The `/ws/{username}` endpoint manually reads the `Origin` header and validates it against `CORS_ORIGINS` before calling `websocket.accept()`. If the origin isn't in the allowlist, it closes with a 403.

---

## What's been built

### Phase 1 — Foundation
Data flows end to end. GitHub username in → profile page out. FastAPI, SQLAlchemy async, Alembic, pgvector schema, React + Vite SPA, health score algorithm (13 signals → A/B/C grade), language breakdown, repo grid.

### Phase 2 — Real-time indexing
Background fan-out with `celery.group` — one Celery task per repo, all parallel. Redis pub/sub bridges progress events to a WebSocket. Frontend shows live progress bar as repos index. One real fix along the way: `CORSMiddleware` doesn't cover WebSocket upgrades — `/ws/{username}` manually validates the Origin header.

### Phase 3 — RAG assistant + streaming components
Local embeddings via `fastembed` (no API key, runs on CPU). Code files chunked by function/class boundary, vectors stored in pgvector. `/query` SSE endpoint streams `thinking_step` → `token` → `component_type` → `component_data` → `done` events. Frontend component registry renders whichever of 7 component types the LLM returns. Rate limited at 20 req/min per IP via Redis.

### Phase 4 — LangGraph analysis agent
4-node `StateGraph`: fetch → analyse → persona → score. All nodes are sync (`def`, not `async def`) — runs inside Celery via `graph.invoke()`. Code pattern analysis (type hint rate, error handling rate, docstring rate, test pattern rate) is pure Python regex — zero tokens sent to Groq. Only aggregated stats (~400-600 tokens total) go to the LLM for persona generation and skill scoring. Results stored once per developer, surfaced into every subsequent RAG prompt.

### Phase 5 — Observability + performance
Structured JSON access logging (`method`, `path`, `status`, `duration_ms`) via Starlette middleware. `LLMCall` table records every Groq call (model, tokens_in, tokens_out, cost_usd, duration_ms). `/admin` dashboard with total cost, 24h stats, p95 latency, last 50 calls. Sentry init (production only, behind `SENTRY_DSN_BACKEND`). `React.lazy()` for all AI components. Preconnect hints for image hosts. OG meta tags per profile.

### Phase 6 — Compare + snapshots
`/compare/:user1/:user2` — side-by-side stats with winner highlight on each metric. Auto-snapshot after every index run; staleness check on `/analyze` skips re-indexing if `indexed_at` < 1 hour old (`?force=true` to bypass). Snapshot history renders in the profile sidebar.

---

## Why these technical choices

- **fastembed over OpenAI embeddings** — runs locally on CPU, zero cost, zero API key. `BAAI/bge-small-en-v1.5` produces 384-dim vectors, downloads once (~130MB) to `~/.cache/fastembed/`, and is more than sufficient at this data scale.
- **Groq over Anthropic/OpenAI for generation** — free tier (14,400 req/day) is genuinely usable for a public demo; OpenAI-compatible API means swapping providers later is a one-line change; LPU inference is fast enough that the typing effect looks real.
- **pgvector over Pinecone** — keeps everything in Postgres, no extra service, same Alembic migrations, same connection pool.
- **LangGraph agent runs once at indexing, not per query** — code pattern analysis and skill scoring happen in a background Celery task after indexing completes. The RAG pipeline reuses pre-computed `ai_persona` + `skill_scores` from the DB; it never re-derives them on each chat question.
- **The AI decides what UI to render** — the LLM returns `{ type, text, data }`; a frontend registry maps `type` → React component. This is the same architectural pattern Claude.ai uses for artifacts. The AI drives the UI, not the user.
- **CSS Modules over Tailwind** — full design control, zero runtime cost, one scoped stylesheet per component.
- **Celery fan-out + Redis pub/sub + WebSocket instead of polling** — indexing 50+ repos in parallel and pushing live granular progress, rather than the frontend polling a status endpoint every few seconds.
- **uv over pip** — 10–100× faster installs, lockfile via `uv.lock`. Docker builds go from minutes to seconds.

Full decision log: [`CLAUDE.md`](./CLAUDE.md).

---

## Performance

Lighthouse scores on `/u/:username`, before and after optimisation work:

| | Before | After |
|---|---|---|
| Performance | _TODO_ | _TODO_ |
| Accessibility | _TODO_ | _TODO_ |
| Best Practices | _TODO_ | _TODO_ |
| SEO | _TODO_ | _TODO_ |

Optimisations already in place: all AI components code-split via `React.lazy()`, lazy-loaded avatar images with explicit dimensions to prevent layout shift, preconnect hints for image hosts, OG meta tags injected per-profile. Run Lighthouse on a deployed URL and fill in the numbers.

---

## Local setup

Requires Docker and free API keys from GitHub and Groq (both take under 2 minutes).

```bash
git clone <repo-url>
cd codesense

make setup        # copies .env.example → .env and installs frontend deps (first time only)
# Edit .env — fill in GITHUB_TOKEN and GROQ_API_KEY (links are in the file)

make dev          # starts postgres + redis + api + worker in Docker (hot reload)
make migrate      # run once after first `make dev`

# In a second terminal:
make frontend     # start Vite dev server
```

Then open [http://localhost:5173](http://localhost:5173), type a GitHub username, watch it index live, and click **Ask AI**.

### All make targets

```
make setup              first-time: copy .env.example, npm install
make dev                start all backend services (postgres + redis + api + worker)
make down               stop all containers
make fresh              wipe volumes and start from scratch
make migrate            alembic upgrade head
make makemigration      create a new migration (msg="description")
make frontend           start Vite dev server (separate terminal)
make restart-worker     restart Celery worker without restarting everything
make logs               tail all service logs (make logs service=worker for one)
make shell-api          bash into the api container
make shell-db           psql into postgres
make seed               seed 3 real GitHub profiles
make build              rebuild Docker images from scratch
make install            uv sync locally (for IDE type hints outside Docker)
make lock               uv lock (after changing pyproject.toml deps)
make lint               ruff check
make format             ruff format
make test               pytest (uses in-memory SQLite, no Docker needed)
```

---

## Stack

**Backend:** FastAPI · SQLAlchemy 2.x async · Alembic · Celery · Redis · PostgreSQL 16 + pgvector · Groq `llama-3.3-70b-versatile` · fastembed `BAAI/bge-small-en-v1.5` (local CPU embeddings) · LangGraph 0.6 · `uv`

**Frontend:** React 18 · Vite 5 · TypeScript · TanStack Router / Query / Virtual · Zustand + immer · Framer Motion · Radix UI · CSS Modules · Lucide · hand-built SVG components (no chart library)

**Infra:** Docker Compose · GitHub Actions CI

---

## API endpoints

```
POST /api/analyze                         submit username, start indexing
GET  /api/profile/:username               full profile + repos + stats
GET  /api/profile/:username/agent-trace   skill_scores, ai_persona, LangSmith URL
POST /api/query                           RAG question → SSE stream
GET  /api/compare/:user1/:user2           side-by-side profiles
POST /api/snapshot/:username              save a snapshot manually
GET  /api/snapshots/:username             list saved snapshots
GET  /api/admin/stats                     aggregate LLMCall stats + cost
GET  /api/admin/calls                     last 50 LLMCall rows
WS   /ws/:username                        indexing progress stream
```

---

## License

MIT
