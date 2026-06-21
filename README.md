# codesense

**The complete picture of any developer.**

Enter a GitHub username. codesense indexes every public repository, computes a health score for each one, runs a LangGraph analysis agent to build a developer persona, and gives you an AI assistant that answers questions about the developer by reading their actual code — not just their commit graph.

---

## Demo

<video src="demo.mp4" controls width="100%"></video>

---

## Features

1. **Index** — paste a GitHub username; codesense fans out across every public repo in parallel (Celery), computing a health score (tests, CI, docs, license, activity) for each one with live WebSocket progress
2. **Profile** — a data-dense profile page: stats row, language breakdown, repo grid sorted by health grade, skill radar, contribution heatmap, and snapshot history
3. **Agent analysis** — after indexing, a 4-node LangGraph agent fetches up to 24 source files, analyses code patterns with pure Python regex, then asks Groq to generate a developer persona and skill scores (Backend / Frontend / DevOps / Testing / AI-ML) — stored once, reused everywhere
4. **Ask anything** — a chat panel backed by RAG over the developer's actual source code. Retrieves real code chunks via pgvector cosine similarity, streams a response with token-by-token typing effect and contextual thinking steps
5. **AI-driven UI** — the assistant returns structured JSON `{ type, text, data }`; a frontend component registry maps `type` to a React component and renders it inline — commit heatmap, skill radar, growth timeline, or plain text
6. **Compare** — `/compare/:user1/:user2` puts two developers side-by-side with a winner highlight on each metric
7. **Snapshots** — profile state is captured automatically after every index run; snapshot history shows how a developer's stack and health scores have changed over time

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
│  LANGGRAPH AGENT PIPELINE  (runs once per developer)            │
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
│  RAG QUERY PIPELINE  (per-request, SSE streaming)               │
│                                                                 │
│  POST /query → embed question (fastembed, local, 384-dim)       │
│    → pgvector cosine search → top-k CodeChunk rows              │
│    → build prompt: system + chunks + ai_persona + skill_scores  │
│    → Groq llama-3.3-70b streaming completion                    │
│    → parse structured JSON { type, text, data }                 │
│    → SSE events: thinking_step → token → component_type         │
│                  → component_data → done                        │
│    → LLMCall row written (tokens_in, tokens_out, cost_usd)      │
└─────────────────────────────────────────────────────────────────┘
```

### Agent vs. RAG pipeline

These are two separate systems that run at different times and serve different purposes:

|                | LangGraph agent                                              | RAG pipeline                                    |
|----------------|--------------------------------------------------------------|-------------------------------------------------|
| When it runs   | Once, after indexing completes                               | On every chat question                          |
| What it does   | Fetches code → regex analysis → Groq for persona + scores   | Embeds question → pgvector search → Groq stream |
| Output         | `ai_persona` + `skill_scores` stored in Postgres             | SSE stream → rendered component                 |
| Token cost     | ~400–600 total per developer                                 | ~3,000–6,000 per query                          |

The agent enriches the context that RAG uses. RAG retrieves relevant code chunks per question; the agent's pre-computed persona and skill scores give the LLM a holistic picture of the developer beyond what any single chunk contains.

Running the agent at indexing time (not per query) is a deliberate cost and latency decision. Fetching 24 files and running analysis would add 3–5 seconds to every chat response and re-compute things that never change between questions. By doing it once, queries stay under 2 seconds.

---

## Data flow

End-to-end map of every piece of data — where it comes from, what transforms it, where it lands, and what the AI receives.

### 1 — GitHub API → Postgres

`POST /api/analyze` triggers a Celery fan-out. Each `index_single_repo` task makes three GitHub API calls and persists results to two tables.

**GitHub API calls per repo:**

| Call | What it returns |
|------|-----------------|
| `GET /repos/:owner/:repo` | name, description, stars, forks, open_issues, topics, created_at, pushed_at, is_fork, is_archived, primary_language |
| `GET /repos/:owner/:repo/languages` | `{ "Python": 14200, "TypeScript": 3400 }` — byte counts per language |
| `GET /repos/:owner/:repo/commits?per_page=1` | total commit count via `Link` response header (no body needed) |
| `GET /repos/:owner/:repo/contents` | directory listing used to detect README, tests/, .github/workflows/, Dockerfile, LICENSE, CONTRIBUTING.md |

**Stored in `developers` table:**

```
github_username, display_name, avatar_url, bio, github_url, location, company
followers, following, public_repos, github_joined_at
peak_commit_day, commit_frequency_per_week
ai_persona (TEXT)          ← populated by LangGraph agent later
skill_scores (JSONB)       ← populated by LangGraph agent later
index_status, indexed_at
```

**Stored in `repos` table (one row per repo):**

```
github_id, name, full_name, description, github_url, homepage_url
is_fork, is_archived, primary_language
all_languages (JSONB)      ← { "Python": 14200, "TypeScript": 3400 }
stars, forks, open_issues, commit_count, watcher_count
last_commit_at, github_created_at, github_pushed_at
has_readme, has_tests, has_ci, has_docker, has_license, has_contributing
health_score (0–100), health_grade (A/B/C)
topics (JSONB)             ← ["fastapi", "python", "docker"]
```

**Health score computation (13 signals, weighted):**

```
has_readme        → +10
has_tests         → +20
has_ci            → +20
has_docker        → +10
has_license       → +10
has_contributing  → +5
stars             → up to +10 (logarithmic)
commit_count      → up to +10
recent activity   → up to +5 (days since last push)
```

---

### 2 — Source files → Code chunks → pgvector

After each repo is indexed, `embed_repo` fetches source files and builds a searchable vector index.

**File selection:** Top source files by extension (`.py`, `.ts`, `.tsx`, `.js`, `.go`, `.rs`, `.java`, etc.), skipping `node_modules`, `dist`, `.git`, lockfiles, and minified files.

**Chunking strategy (`ai/rag/chunker.py`):**

```
Python           → split on `def ` / `class ` / `async def ` boundaries
JavaScript/TS    → split on `function`, `const X = (`, `class ` boundaries
Everything else  → sliding window: 50 lines per chunk, 10-line overlap
Hard cap         → 1,600 chars (~400 tokens) per chunk; oversized chunks split further
```

**Embedding:** Each chunk is passed through `fastembed` (`BAAI/bge-small-en-v1.5`) locally on CPU. Output is a 384-dimensional float vector. No API call; runs inside the FastAPI container in ~30–50ms per batch.

**Stored in `code_chunks` table (one row per chunk):**

```
repo_id           → FK to repos
file_path         → e.g. "src/auth/middleware.py"
chunk_index       → position within the file
content (TEXT)    → raw source code of the chunk
token_count       → estimated tokens
embedding         → vector(384) — stored in pgvector column with ivfflat index
language          → "Python", "TypeScript", etc.
chunk_type        → "function", "class", "sliding_window"
```

The `ivfflat` index (migration 002) enables sub-millisecond cosine similarity search across millions of chunks.

---

### 3 — LangGraph agent → Postgres

After indexing completes, `analyse_developer` runs as a Celery task. It is a 4-node LangGraph `StateGraph` that runs once per developer.

**What the agent receives (state input):**

```python
{
  "developer_id": int,
  "repos": [{ name, health_score, stars, primary_language, topics }],   # top 8 by health + stars
  "code_samples": [{ repo_name, file_path, content }]                   # up to 24 files, 3,000 chars each
}
```

**fetch_node** — picks the 8 highest-scoring repos and fetches 3 source files each from GitHub (raw content). If fewer than 5 samples are retrieved on the first pass, a conditional edge triggers a re-fetch with broader file criteria.

**analyse_node** — pure Python regex, zero LLM calls:

```
type_hint_rate      = parameters_with_type_annotations / total_parameters
error_handling_rate = try_except_blocks / total_functions
docstring_rate      = triple_quote_docstrings / total_functions
test_pattern_rate   = (test_ functions + assert statements) / lines_of_code
growth_milestones   = repo push dates grouped by year → tech stack per year
```

**persona_node** — sends ~150 tokens to Groq:

```
Input:  aggregated stats (type_hint_rate, error_handling_rate, docstring_rate,
         test_pattern_rate, primary languages, health score distribution)
Output: 2-3 sentence plain-English developer persona
```

**score_node** — sends ~150 tokens to Groq:

```
Input:  same aggregated stats
Output: { "backend": 75, "frontend": 60, "devops": 80, "testing": 55, "ai_ml": 40 }
        (heuristic fallback if Groq call fails — task never hard-fails)
```

**What gets written back to `developers` table:**

```
ai_persona   = "Backend-focused engineer who prioritises type safety..."
skill_scores = { backend: 75, frontend: 60, devops: 80, testing: 55, ai_ml: 40 }
```

Raw source code never leaves the server. Only the computed scalar stats (~400–600 tokens total per developer) are sent to Groq.

---

### 4 — Chat question → RAG prompt → Groq → SSE → frontend

Every chat question goes through a fixed pipeline: embed → retrieve → build prompt → stream.

**Step 1 — embed the question**

```
question string → fastembed (local CPU) → 384-dim vector   (~30–50ms, no API call)
```

**Step 2 — pgvector retrieval**

```sql
SELECT content, file_path, repo_id
FROM code_chunks
ORDER BY embedding <=> $question_vector
WHERE 1 - (embedding <=> $question_vector) > 0.3   -- cosine similarity floor
LIMIT 8
```

Returns up to 8 code chunks whose content is semantically closest to the question.

**Step 3 — prompt construction**

```
SYSTEM_PROMPT
└── instructs the model to return structured JSON { type, text, data }
    and lists all component types with their exact data shapes

developer_context block (built from DB):
  Username, display_name, bio
  AI Persona (pre-computed by agent)         ← empty until agent runs
  AI Skill Scores (pre-computed by agent)    ← empty until agent runs
  total_repos, total_stars, total_commits, avg_health_score
  repos_with_tests / repos_with_ci counts
  peak_commit_day, commit_frequency_per_week
  language breakdown (top 6 languages with %)
  top 10 repos by health score:
    name | language | grade | score | stars | commits | [tests, CI, Docker, license]

code_context block:
  up to 8 retrieved chunks, each with repo name, file path, and raw content

Question: {user_question}
```

Total tokens sent to Groq: ~3,000–6,000 per query.

**Step 4 — Groq streaming**

```
AsyncOpenAI(base_url="https://api.groq.com/openai/v1")
  model: llama-3.3-70b-versatile
  stream: true
```

The model streams back a single JSON object (character by character). The pipeline buffers tokens and emits SSE events in parallel:

```
event: thinking_step   data: { "message": "Retrieving relevant code…", "done": false }
event: thinking_step   data: { "message": "Analyzing patterns…", "done": true }
event: token           data: { "char": "T" }
event: token           data: { "char": "h" }
...  (full response accumulated)
event: component_type  data: { "type": "skill_radar" }
event: component_data  data: { "axes": [...], "summary": "..." }
event: done            data: {}
```

**Step 5 — frontend rendering**

```
fetch() + ReadableStream parses SSE events
  → thinking_step: ThinkingSteps component updates
  → token: rawText accumulates (not shown — it's JSON)
  → component_type: registry.ts looks up React.lazy(component)
  → component_data: component receives data prop and renders
  → done: isStreaming = false, final state locked
```

**Step 6 — cost tracking**

A `LLMCall` row is written after every Groq response:

```
model, prompt_tokens, completion_tokens, total_tokens
cost_usd, duration_ms, endpoint ("/api/query"), created_at
```

Aggregated stats are exposed at `GET /api/admin/stats`.

---

### Database schema at a glance

```
developers
  ├── repos (developer_id FK)
  │     └── code_chunks (repo_id FK)  ← vector(384) embedding column
  ├── indexing_jobs (developer_id FK)
  └── profile_snapshots (developer_id FK)

llm_calls  (standalone — no FK)
```

`profile_snapshots.snapshot_data` stores the full profile JSON at the moment of capture — total repos, stars, language breakdown, health grade distribution, and all repo rows. Comparing snapshots over time shows how a developer's stack and quality signals have changed.

---

## How it works

### Indexing a developer

```
1.  POST /api/analyze
    FastAPI upserts Developer row, creates IndexingJob, returns {job_id} immediately (~50ms).
    Frontend opens WebSocket to /ws/{username}.

2.  Celery enqueues index_developer(developer_id, job_id).

3.  index_developer (Celery worker):
    → fetches all public repos from GitHub API (paginated)
    → builds celery.group — one index_single_repo task per repo
    → registers on_indexing_complete as the chord callback
    → group dispatches; all repo tasks run in parallel

4.  Each index_single_repo (concurrent, one per repo):
    → GitHub API: GET /repos/:owner/:repo/languages
    → GitHub API: GET /repos/:owner/:repo/commits?per_page=1 (commit count via Link header)
    → GitHub API: GET /repos/:owner/:repo/contents (check README, tests, CI, Docker, license)
    → compute_health_score() → A/B/C/D/F grade (13 signals, weighted)
    → upsert Repo row in Postgres
    → redis.publish("codesense:progress:{username}", {repos_done, repos_total})

5.  Redis pub/sub → WebSocket handler → frontend progress bar updates live.

6.  on_indexing_complete (chord callback, fires when all repo tasks finish):
    → marks IndexingJob done, updates developer.indexed_at
    → saves ProfileSnapshot (stats frozen in time)
    → enqueues analyse_developer.delay(developer_id)
    → redis.publish({type: "done"})

7.  analyse_developer (Celery — LangGraph agent):
    → LangGraph StateGraph.stream(stream_mode="updates")

    ├─ fetch_node:
    │    picks top repos by health score + star count (max 8 repos)
    │    fetches 3 source files per repo from GitHub (max 3,000 chars each)
    │    conditional edge: if < 5 samples on first attempt → re-fetch with broader criteria

    ├─ analyse_node (pure Python, zero LLM calls):
    │    type_hint_rate     — regex: parameters with `: type` annotations
    │    error_handling_rate — try/except block count
    │    docstring_rate     — triple-quote docstrings
    │    test_pattern_rate  — test_ functions and assert statements
    │    compute_growth()   — milestones by year from repo push dates

    ├─ persona_node:
    │    sends aggregated stats (~150 tokens) to Groq
    │    returns 2-3 sentence developer persona

    └─ score_node:
         sends stats to Groq → {backend:75, frontend:60, devops:80, testing:55, ai_ml:40}
         heuristic fallback if Groq call fails

    → saves developer.ai_persona + developer.skill_scores to Postgres
    → publishes {type:"agent_done"}

8.  Frontend receives "agent_done":
    → profile refetches → "AI analyzed" badge appears
    → IndexingProgress banner shows "Indexed N repos · AI analyzed" then fades
```

### Answering a chat question

```
1.  POST /api/query {username, question}
    Rate limit: Redis INCR with 60s TTL — > 20 req/min → 429.

2.  Load Developer from Postgres (including ai_persona, skill_scores).

3.  Embed the question locally:
    fastembed BAAI/bge-small-en-v1.5 → 384-dim vector
    CPU-only inside the FastAPI container — no API call, ~30–50ms.

4.  pgvector cosine search:
    SELECT * FROM code_chunks
    ORDER BY embedding <=> $question_vector
    WHERE 1 - (embedding <=> $question_vector) > 0.3
    LIMIT 8

5.  Build prompt:
    SYSTEM_PROMPT
    + build_developer_context(developer)  ← injects ai_persona + skill_scores
    + top-8 retrieved code chunks (with repo/file context)
    + "Question: {question}"

6.  AsyncOpenAI(base_url="https://api.groq.com/openai/v1")
    .chat.completions.create(model="llama-3.3-70b-versatile", stream=True)

7.  Stream parsing and SSE emission:
    → event:thinking_step  data:{message:"Retrieving relevant code…", done:false}
    → event:thinking_step  data:{message:"Analyzing patterns…", done:true}
    → event:token          data:{char:"T"}  (character by character)
    → final chunk: parse JSON {type, text, data}
    → event:component_type data:{type:"skill_radar"}
    → event:component_data data:{backend:75, frontend:60, ...}
    → event:done           data:{}
    → write LLMCall row (tokens_in, tokens_out, cost_usd, duration_ms)

8.  Frontend reads via fetch() + ReadableStream (not EventSource — EventSource can't POST).
    ThinkingSteps render during processing.
    On component_type: registry.ts maps type → React.lazy(component).
    On component_data: component renders with live data.
```

RAG grounds every response in actual code from the developer's repos. The system prompt instructs the LLM to base its answer only on retrieved chunks and developer stats. All measurements (type hint rate, error handling rate, etc.) come from pure Python regex — the LLM only handles natural language generation from verified data, never the analysis itself. Thinking steps are surfaced in the UI to make the retrieval process transparent.

### AI-driven UI

The LLM returns structured JSON rather than plain text:

```json
{ "type": "skill_radar", "text": "Here are their skill scores...", "data": { "backend": 75, "frontend": 60 } }
```

`registry.ts` maps `type` → `React.lazy(component)`:

```typescript
const registry = {
  skill_radar:        React.lazy(() => import("../ai-components/SkillRadar")),
  commit_heatmap:     React.lazy(() => import("../ai-components/CommitHeatmap")),
  hire_recommendation: React.lazy(() => import("../ai-components/HireRecommendation")),
  // ...
}
```

The model selects which component to render based on the question. "Show me their skill breakdown" → `skill_radar`. "How active are they?" → `commit_heatmap`. The user never picks a chart type. Adding a new component type requires three steps: add the type literal to `AIMessage` in `backend/app/ai/schemas/output.py`, build the React component, and register it in `registry.ts`.

---

## Design decisions

- **fastembed over OpenAI embeddings** — runs locally on CPU, zero cost, zero API key. `BAAI/bge-small-en-v1.5` produces 384-dim vectors, downloads once (~130MB), and is sufficient at this data scale. Embedding at query time costs ~30–50ms with no network round-trip.

- **Groq over Anthropic/OpenAI for generation** — free tier (14,400 req/day) is usable for a public demo; OpenAI-compatible API means swapping providers is a one-line change. The agent sends ~400–600 tokens per developer (aggregated stats only — raw code never leaves the server). Each RAG query sends ~3,000–6,000 tokens, costing under $0.005 at paid rates.

- **pgvector over Pinecone** — keeps everything in Postgres; same Alembic migrations, same connection pool, no additional service to operate.

- **Agent at indexing time, not per query** — code pattern analysis and skill scoring run once in a background Celery task. The RAG pipeline reuses pre-computed results from the DB. This keeps query latency under 2 seconds and eliminates redundant computation.

- **Celery fan-out + Redis pub/sub + WebSocket** — indexing 50+ repos in parallel with live per-repo progress, rather than polling a status endpoint. `CORSMiddleware` in FastAPI does not cover WebSocket upgrades — `/ws/{username}` manually validates the `Origin` header before calling `websocket.accept()`.

- **CSS Modules over Tailwind** — full design control, zero runtime cost, one scoped stylesheet per component. SVG charts are built by hand with d3 for math; no Recharts or Chart.js.

- **uv over pip** — 10–100× faster installs, lockfile via `uv.lock`. Docker builds go from minutes to seconds.

Full decision log: [`CLAUDE.md`](./CLAUDE.md).

---

## What's been built

**Phase 1 — Foundation**
Data flows end to end. GitHub username in → profile page out. FastAPI, SQLAlchemy async, Alembic, pgvector schema, React + Vite SPA, health score algorithm (13 signals → A/B/C grade), language breakdown, repo grid.

**Phase 2 — Real-time indexing**
Background fan-out with `celery.group` — one Celery task per repo, all parallel. Redis pub/sub bridges progress events to a WebSocket. Frontend shows a live progress bar as repos index.

**Phase 3 — RAG assistant + streaming components**
Local embeddings via `fastembed` (CPU, no API key). Code files chunked by function/class boundary, vectors stored in pgvector. `/query` SSE endpoint streams `thinking_step → token → component_type → component_data → done`. Frontend component registry renders whichever of 7 component types the LLM returns. Rate limited at 20 req/min per IP via Redis.

**Phase 4 — LangGraph analysis agent**
4-node `StateGraph`: fetch → analyse → persona → score. All nodes are sync (`def`, not `async def`) — runs inside Celery via `graph.invoke()`. Code pattern analysis is pure Python regex — zero tokens sent to Groq for the analysis phase. Only aggregated stats (~400–600 tokens total) go to the LLM for persona generation and skill scoring. Results stored once per developer, injected into every subsequent RAG prompt.

**Phase 5 — Observability + performance**
Structured JSON access logging (`method`, `path`, `status`, `duration_ms`) via Starlette middleware. `LLMCall` table records every Groq call (model, tokens_in, tokens_out, cost_usd, duration_ms). `/admin` dashboard with total cost, 24h stats, p95 latency, last 50 calls. Sentry init (production only). `React.lazy()` for all AI components. Preconnect hints for image hosts. OG meta tags per profile.

**Phase 6 — Compare + snapshots**
`/compare/:user1/:user2` — side-by-side stats with winner highlight on each metric. Auto-snapshot after every index run; staleness check on `/analyze` skips re-indexing if `indexed_at` < 1 hour old (`?force=true` to bypass). Snapshot history renders in the profile sidebar.

---

## Local setup

Requires Docker and free API keys from GitHub and Groq (both take under 2 minutes).

```bash
git clone <repo-url>
cd codesense

make setup        # copies .env.example → .env and installs frontend deps (first time only)
# Edit .env — fill in GITHUB_TOKEN and GROQ_API_KEY

make dev          # starts postgres + redis + api + worker in Docker (hot reload)
make migrate      # run once after first `make dev`

# In a second terminal:
make frontend     # start Vite dev server
```

Open [http://localhost:5173](http://localhost:5173), enter a GitHub username, and watch it index live.

### Make targets

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

**Backend:** FastAPI · SQLAlchemy 2.x async · Alembic · Celery · Redis · PostgreSQL 16 + pgvector · Groq `llama-3.3-70b-versatile` · fastembed `BAAI/bge-small-en-v1.5` · LangGraph 0.6 · `uv`

**Frontend:** React 18 · Vite 5 · TypeScript · TanStack Router / Query · Zustand + immer · Framer Motion · Radix UI · CSS Modules · Lucide · hand-built SVG charts

**Infra:** Docker Compose · GitHub Actions CI

---

## API endpoints

```
POST /api/analyze                         submit username, start indexing
GET  /api/profile/:username               full profile + repos + stats
GET  /api/profile/:username/agent-trace   skill_scores, ai_persona, agent metadata
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
