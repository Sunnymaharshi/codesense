# PLAN.md — codesense build plan

> Sequenced to match your learning roadmap.
> Each phase builds on the last. Don't skip ahead — the AI layer slots in cleanly only after the foundation is solid.

---

## Where you are right now

**Completed from roadmap:**

- FastAPI basics — blog site with full CRUD
- Redis rate limiting
- JWT auth
- Docker + Docker Compose
- SQLAlchemy + Alembic (done)

**Starting point:** Phase 1 below.

---

## Phase 1 — Foundation (start this week)

**Goal:** Data flows end to end. GitHub username in → profile page out. No AI yet.

### Backend tasks

- [x] Init monorepo: `codesense/` with `frontend/`, `backend/`, `ai/` dirs
- [x] `docker-compose.yml` — services: `api`, `worker`, `postgres`, `redis`
- [x] `docker-compose.dev.yml` — hot reload overrides + shared `uv_cache` volume
- [x] Backend uses `uv` — `pyproject.toml` + `uv.lock`, no `requirements.txt`
- [ ] Run `cd backend && uv sync` locally to generate `uv.lock` and get IDE support ← do this first
- [x] `Makefile` — all commands including `lint`, `format`, `lock`
- [x] SQLAlchemy models: `Developer`, `Repo`, `IndexingJob`, `ProfileSnapshot`, `CodeChunk`, `LLMCall`
- [x] `backend/app/core/config.py` — pydantic-settings
- [x] `backend/app/db/session.py` — async engine + `get_db()`
- [x] Alembic migration `001_initial.py` — all tables + `CREATE EXTENSION IF NOT EXISTS vector`
- [x] `backend/app/main.py` — FastAPI app, CORS, routers, Sentry init (prod only), `/health` endpoint
- [x] `backend/app/api/deps.py` — `DbSession` + `GitHubDep` annotated type aliases
- [x] `backend/app/services/github.py` — async httpx: `get_user`, `get_repos` (paginated), `get_languages`, `get_commit_count`, `get_repo_signals` (13 parallel checks)
- [x] `backend/app/services/health_score.py` — pure scorer, `compute_language_percentages`, `get_top_language`
- [x] `backend/app/api/routes/analyze.py` — `POST /api/analyze` (sync, Celery in Phase 2). Upserts Developer, indexes all repos with parallel signal detection.
- [x] `backend/app/api/routes/profile.py` — `GET /api/profile/{username}` with aggregated stats
- [x] `backend/app/schemas/profile.py` — all request/response Pydantic shapes
- [x] `backend/tests/conftest.py` — in-memory SQLite, async client, dependency_overrides
- [x] `backend/tests/test_health_score.py` — 20 unit tests, all scoring branches
- [x] `backend/tests/test_analyze.py` — mocked GitHub API, happy path + 404 + idempotent
- [x] `backend/tests/test_profile.py` — developer fields, repos, stats, 404, case insensitivity

### Frontend tasks

- [ ] Vite + React + TypeScript scaffold: `npm create vite@latest . -- --template react-ts`
- [x] `src/styles/tokens.css` — full design token system, light + dark mode
- [x] `src/styles/global.css` — reset, base styles, `.shimmer`, `.cursor` animations
- [ ] Install all npm libs (see stack table in CLAUDE.md)
- [ ] `frontend/src/main.tsx` — import `global.css`, QueryClientProvider, RouterProvider
- [ ] `frontend/src/router.ts` — TanStack Router, `/` and `/u/$username` routes
- [ ] `frontend/src/lib/api.ts` — `analyzeUser()` and `getProfile()` typed fetch wrappers
- [ ] `frontend/src/store/profileStore.ts` — Zustand + immer: `username`, `indexStatus`, `reposDone`, `reposTotal`
- [ ] `frontend/src/pages/Home.tsx` — search bar, on submit call analyzeUser → navigate
- [ ] `frontend/src/pages/Profile.tsx` — layout shell, TanStack Query for profile data
- [ ] `frontend/src/components/ui/Badge/` — health grade pill (A/B/C)
- [ ] `frontend/src/components/ui/Skeleton/` — shimmer placeholder
- [ ] `frontend/src/components/profile/StatsRow/`
- [ ] `frontend/src/components/profile/LanguageBars/`
- [ ] `frontend/src/components/profile/RepoCard/`
- [ ] `frontend/src/components/profile/RepoGrid/`
- [ ] `frontend/src/components/profile/ProfileHeader/`
- [ ] `frontend/src/components/profile/ContributionStats/`

### Done when

```bash
make dev && make migrate
# open http://localhost:5173
# type "torvalds" → full profile renders with real GitHub data
# repos listed with health scores A/B/C
# language bars showing Python/C/Shell breakdown
```

---

## Phase 2 — Celery + WebSockets + real-time (roadmap weeks 7–9)

**Goal:** Indexing happens in the background. Frontend feels live.

### Backend tasks

- [x] `workers/celery_app.py` — Celery instance, Redis broker config, task settings
- [x] `workers/index_repo.py` — Phase 1 stub tasks (`index_developer`, `index_single_repo`, `health_check`). Worker starts cleanly. Phase 2 replaces stubs with real logic.
- [ ] Fan-out: `celery.group` — one sub-task per repo, all run in parallel
- [ ] Update `IndexingJob` rows as tasks complete (pending → running → done)
- [ ] Redis pub/sub: Celery tasks publish progress events to a channel
- [ ] `ws.py` — WebSocket `/ws/:username` subscribes to pub/sub channel, pushes to frontend

### Frontend tasks

- [ ] `hooks/useWebSocket.ts` — connect to `/ws/:username`, handle progress events
- [ ] Optimistic UI: profile skeleton appears immediately on submit — don't wait for indexing
- [ ] Progress bar / counter: "Indexing 12 / 34 repos…" driven by WebSocket
- [ ] Skeleton components with shimmer animation using `framer-motion` for each section
- [ ] `RepoGrid/` — upgrade to `@tanstack/react-virtual` (handles 100+ repos)
- [ ] Zustand: add `indexingStatus`, `reposDone`, `reposTotal` to profileStore

### Done when

Submit username → skeleton appears instantly → repos fill in live → "Ready" state when complete.

---

## Phase 3 — RAG assistant + streaming component rendering (roadmap weeks 12–14)

**Goal:** The core AI feature. User asks a question → right component streams back with Claude-like feel.

### AI tasks

- [ ] `ai/schemas/output.py` — `AIMessage` Pydantic model with `type` literal union
- [ ] `ai/rag/embedder.py` — chunk code files by function, embed via `text-embedding-3-small`
- [ ] `CodeChunk` model + Alembic migration — pgvector column `vector(1536)`
- [ ] Extend Celery indexing task to embed chunks after scraping
- [ ] `ai/rag/retriever.py` — cosine similarity search, top-k, filter by developer_id
- [ ] `ai/rag/prompt_builder.py` — system prompt enforcing JSON output schema + thinking steps
- [ ] `ai/rag/streamer.py` — Anthropic API streaming → SSE events (thinking_step, token, component_type, component_data, done)
- [ ] LangSmith tracing on every LLM call

### Backend tasks

- [ ] `api/routes/query.py` — `POST /query`, streams SSE response using `@microsoft/fetch-event-source` protocol
- [ ] SSE event types: `thinking_step`, `token`, `component_type`, `component_data`, `done`
- [ ] Rate limit `/query` — Redis, 20 req/min per IP

### Frontend tasks

- [ ] Install: `ai` (Vercel AI SDK), `@microsoft/fetch-event-source`, `shiki`, `react-diff-view`
- [ ] `store/chatStore.ts` — Zustand + immer: message history `[{ role, type, text, data, isStreaming }]`
- [ ] `components/chat/ChatPanel/` — question input, suggested chips, message thread
- [ ] `components/chat/StreamingIndicator/` — thinking steps with check/spin icons + blinking cursor CSS
- [ ] `components/chat/MessageStream/` — SSE consumer, accumulates events, renders via registry
- [ ] **`components/ai-components/registry.ts`** — `type → Component` map
- [ ] `CommitHeatmap/` — SVG grid, d3-scale for color intensity, framer-motion cell reveal left-to-right
- [ ] `SkillRadar/` — SVG pentagon, d3-shape for polygon path, axes animate in before fill
- [ ] `GrowthTimeline/` — vertical timeline, entries animate in top-to-bottom
- [ ] `CodePattern/` — shiki for syntax highlighting + react-diff-view for unified diff
- [ ] `RepoComparison/` — two-column scorecard, win/lose colours
- [ ] `DeveloperPersona/` — AI paragraph (typed in) + 4 animated trait bars
- [ ] `HireRecommendation/` — verdict card chained after persona
- [ ] Suggested question chips above chat input

### Done when

User asks "when do they ship?" → thinking steps appear → text types itself in → commit heatmap skeleton mounts → cells fill left to right. Citations appear as inline tags.

---

## Phase 4 — LangGraph analysis agent (roadmap weeks 17–19)

**Goal:** Deep multi-step AI analysis. Agent replaces heuristic health scoring.

### AI tasks

- [ ] `ai/agent/tools.py` — tool definitions:
  - `fetch_repo_content(repo, file_path)` → raw file content
  - `analyse_patterns(code)` → error handling style, test coverage, type hint usage
  - `compute_growth(repos)` → timeline of tech stack milestones by year
- [ ] `ai/agent/nodes.py` — LangGraph nodes:
  - `fetch_node` — pull all repo data from GitHub
  - `analyse_node` — run pattern tools on code samples
  - `persona_node` — generate AI persona paragraph
  - `score_node` — compute final skill scores (BE/FE/AI/DevOps/Testing)
- [ ] `ai/agent/graph.py` — state machine: linear flow + conditional re-fetch edge if data is sparse
- [ ] LangSmith: full graph trace per agent run
- [ ] Save output: `ai_persona` text + `skill_scores` jsonb → `Developer` table

### Backend tasks

- [ ] Extend Celery indexing task to trigger LangGraph agent after embedding
- [ ] `GET /profile/:username/agent-trace` — return LangSmith run URL for the profile page

### Frontend tasks

- [ ] Agent trace panel on profile page — live step list, each node completion pushed via WebSocket
- [ ] `SkillRadar` now populated with real agent scores instead of heuristics
- [ ] `DeveloperPersona` AI paragraph now from agent, not placeholder

### Done when

Indexing runs the full 4-node agent. Profile shows AI persona + real skill scores. Trace panel visible.

---

## Phase 5 — Performance + observability + deploy (weeks 20–22)

**Goal:** Production-ready. Public URL. Lighthouse 95+. Observable.

### Performance tasks

- [ ] Measure Lighthouse on `/u/:username` — screenshot the baseline score
- [ ] `React.lazy()` + `Suspense` for all `ai-components/` — don't load registry until chat opens
- [ ] Lazy-load `ChatPanel` — only mounts after profile data loads
- [ ] Defer WebSocket connection until after first paint
- [ ] Install `rollup-plugin-visualizer` → `vite build` → open `stats.html` → find heavy deps
- [ ] Pure SVG components — no chart library weight in bundle
- [ ] Measure again — document before/after in README with screenshots + live URL

### Observability tasks

- [ ] Sentry: Vite plugin (frontend) + FastAPI middleware (backend)
- [ ] Structured JSON logging: every FastAPI request logs `{ method, path, status, duration_ms }`
- [ ] `LLMCall` table: log every Anthropic API call — model, tokens_in, tokens_out, cost_usd, duration_ms
- [ ] Admin page `/admin` — LLMCall table, total cost, error rate, p95 latency (internal only)

### Deploy tasks

- [ ] GitHub Actions: push to `main` → run tests → build Docker images → push to registry
- [ ] Deploy to Railway or Render (quick) or AWS ECS (more impressive on resume)
- [ ] All secrets via environment variables, never in repo
- [ ] Custom domain: `codesense.dev`
- [ ] SSL via hosting provider or Caddy reverse proxy

### Done when

`codesense.dev/u/torvalds` loads under 1.5s. Lighthouse 95+. Sentry live. LangSmith tracing. CI green.

---

## Phase 6 — Compare + Snapshot tracking (after Phase 3)

Build these when the core profile is stable. Both add real value and virality.

### Compare (`/compare/:user1/:user2`)

- [ ] `GET /compare/:user1/:user2` — return both profiles in one response
- [ ] `Compare.tsx` page — side-by-side `ProfileHeader`, `StatsRow`, `LanguageBars`
- [ ] Shared RAG chat panel — "compare these two" → `repo_comparison` component renders
- [ ] Shareable URL — hiring managers will link to this

### Snapshot tracking

- [ ] `ProfileSnapshot` model + Alembic migration (full profile as JSONB + timestamp)
- [ ] `POST /snapshot/:username` — save current profile state
- [ ] `GET /snapshots/:username` — list all snapshots
- [ ] "Save snapshot" button on profile page
- [ ] Snapshot history timeline on profile
- [ ] Diff view between two snapshots — "how has this developer changed since March?"

---

## Shortcuts to avoid

| Temptation                                | Why to resist                                                                      |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| Adding Next.js                            | FastAPI is your backend. No SSR needed. Decision made.                             |
| Tailwind CSS                              | Decision made. CSS Modules gives you full control and cleaner code.                |
| Recharts / Chart.js                       | Build SVG manually. Shows FE depth. Keeps bundle small.                            |
| External chart lib for radar/heatmap      | D3 math + React SVG is the correct pattern for custom visuals.                     |
| Skipping CSS Modules per-component        | Global styles create specificity hell. Every component gets its own `.module.css`. |
| Using pip / requirements.txt              | Decision made. `uv` + `pyproject.toml` is the standard. Don't mix them.            |
| Building AI before foundation             | Debug order: FastAPI → Celery → WebSocket → then AI. Don't jump ahead.             |
| Generic spinner instead of thinking steps | Thinking steps are the feel difference. Do it right.                               |
| Over-engineering the agent                | 4 nodes, linear flow. Add complexity when needed.                                  |

---

## Interview talking points (per phase)

**After Phase 1:**

> "I built a GitHub repo health scorer — checks README presence, test file patterns, CI config, Docker, license, and commit recency. Every repo gets an A/B/C grade. Pure signal detection, no AI."

**After Phase 2:**

> "Indexing fans out with Celery — `celery.group` runs one task per repo all in parallel. Celery publishes progress to Redis pub/sub. The WebSocket subscribes and pushes live to the frontend. Profile skeleton appears in under 200ms."

**After Phase 3:**

> "Claude returns structured JSON — a type field and a data payload. The frontend has a component registry that maps type to a React component and renders it inline, streaming. The AI decides what UI to show. Same pattern Claude.ai uses for artifacts."

**After Phase 4:**

> "The analysis agent runs a 4-node LangGraph graph — fetch, analyse, persona, score. Each node completion fires a WebSocket event. Users watch it think step by step in real time. Every run is traced in LangSmith."

**After Phase 5:**

> "I pushed Lighthouse from [X] to 95 by lazy-loading the component registry, deferring WebSocket, and code-splitting the chat panel. Before/after is documented in the README with a live URL."

**After Phase 6:**

> "Every profile has a shareable URL. The compare page lets you put two developers side by side — the AI chat understands context and renders a comparison component. You can save snapshots and diff a developer's growth over time."
