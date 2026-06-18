# CLAUDE.md — codesense

> Feed this file at the start of every new conversation to restore full project context.
> Last updated: June 2026

---

## Project identity

**Name:** codesense
**Tagline:** "The complete picture of any developer."
**URL:** codesense.dev
**Concept:** Enter a GitHub username → AI indexes all public repos → renders an intelligent, interactive developer profile with a RAG-powered assistant that streams dynamic React components based on what you ask.

---

## What's been built (Phase 1 — backend complete, frontend pending)

### Infrastructure

| File                     | Status | Notes                                                                                                                                                       |
| ------------------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docker-compose.yml`     | ✅     | postgres (pgvector/pgvector:pg16), redis, api, worker. Health checks on both.                                                                               |
| `docker-compose.dev.yml` | ✅     | Hot reload via volume mounts. Shared `uv_cache` volume.                                                                                                     |
| `backend/Dockerfile`     | ✅     | `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`. No apt-get. Layer-cached dep install.                                                                      |
| `backend/Dockerfile.dev` | ✅     | Same base, no `COPY . .` — code mounted as volume for hot reload.                                                                                           |
| `backend/pyproject.toml` | ✅     | Replaces requirements.txt. Pinned deps. `aiosqlite` in dev deps for test DB.                                                                                |
| `backend/alembic.ini`    | ✅     | URL overridden from pydantic-settings in `env.py`.                                                                                                          |
| `.env.example`           | ✅     | All env vars with inline comments.                                                                                                                          |
| `.gitignore`             | ✅     | Python, Node, Docker, IDE, .env.                                                                                                                            |
| `Makefile`               | ✅     | `dev`, `prod`, `down`, `migrate`, `makemigration`, `test`, `worker`, `logs`, `shell-api`, `shell-db`, `seed`, `build`, `install`, `lock`, `lint`, `format`. |

### Backend — config & DB

| File                                 | Status | Notes                                                                            |
| ------------------------------------ | ------ | -------------------------------------------------------------------------------- |
| `app/__init__.py`                    | ✅     | Package marker.                                                                  |
| `app/core/__init__.py`               | ✅     | Package marker.                                                                  |
| `app/core/config.py`                 | ✅     | `pydantic-settings` — reads `.env` automatically. All env vars typed.            |
| `app/db/__init__.py`                 | ✅     | Package marker.                                                                  |
| `app/db/session.py`                  | ✅     | Async SQLAlchemy engine + `get_db()` dependency. Pool 10, overflow 20, pre-ping. |
| `migrations/__init__.py`             | ✅     | Package marker.                                                                  |
| `migrations/env.py`                  | ✅     | Async Alembic. Imports all models for autogenerate. URL from settings.           |
| `migrations/versions/001_initial.py` | ✅     | All 6 tables + `CREATE EXTENSION IF NOT EXISTS vector`. Manual for reliability.  |

### Backend — models

| File                      | Status | Notes                                                                                       |
| ------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| `app/models/__init__.py`  | ✅     | Imports all models — required for Alembic autogenerate discovery.                           |
| `app/models/base.py`      | ✅     | `DeclarativeBase` + `utcnow()` helper.                                                      |
| `app/models/profile.py`   | ✅     | `Developer`, `Repo`, `IndexingJob`, `ProfileSnapshot` + `IndexStatus`, `HealthGrade` enums. |
| `app/models/embedding.py` | ✅     | `CodeChunk` with safe pgvector import guard. Embedding col is `Text` until Phase 3.         |
| `app/models/llm_call.py`  | ✅     | Cost tracking — model, tokens_in/out, cost_usd, duration_ms, langsmith_run_id.              |

### Backend — API

| File                         | Status | Notes                                                                                                                                               |
| ---------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/api/__init__.py`        | ✅     | Package marker.                                                                                                                                     |
| `app/api/deps.py`            | ✅     | `DbSession` + `GitHubDep` annotated type aliases. Clean injection pattern.                                                                          |
| `app/api/routes/__init__.py` | ✅     | Package marker.                                                                                                                                     |
| `app/api/routes/analyze.py`  | ✅     | `POST /api/analyze` — upserts Developer, creates IndexingJob, indexes repos synchronously. Parallel signal detection per repo via `asyncio.gather`. |
| `app/api/routes/profile.py`  | ✅     | `GET /api/profile/{username}` — full developer + repos sorted by health score + aggregated stats.                                                   |

### Backend — services & schemas

| File                           | Status | Notes                                                                                                                                                          |
| ------------------------------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/services/__init__.py`     | ✅     | Package marker.                                                                                                                                                |
| `app/services/github.py`       | ✅     | Async httpx client. `get_user`, `get_repos` (paginated), `get_languages`, `get_commit_count`, `check_file_exists`, `get_repo_signals` (13 checks in parallel). |
| `app/services/health_score.py` | ✅     | Pure function. `compute_health_score` → (int, grade). `compute_language_percentages`. `get_top_language`. No DB/API deps.                                      |
| `app/schemas/__init__.py`      | ✅     | Package marker.                                                                                                                                                |
| `app/schemas/profile.py`       | ✅     | `AnalyzeRequest`, `AnalyzeResponse`, `DeveloperResponse`, `RepoResponse`, `ProfileStatsResponse`, `ProfileResponse`.                                           |
| `app/main.py`                  | ✅     | FastAPI app, CORS, routers (`/api` prefix), Sentry init (prod only), `/health` endpoint.                                                                       |

### Backend — tests

| File                         | Status | Notes                                                                                                                                        |
| ---------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/__init__.py`          | ✅     | Package marker.                                                                                                                              |
| `tests/conftest.py`          | ✅     | In-memory SQLite via `aiosqlite`. `db_session` + `client` fixtures. `dependency_overrides` injects test DB. No Postgres needed to run tests. |
| `tests/test_health_score.py` | ✅     | 20 unit tests. Every scoring branch + edge cases. Start here: `make test`.                                                                   |
| `tests/test_analyze.py`      | ✅     | `POST /analyze` with mocked GitHub API. Tests happy path, 404, idempotent upsert.                                                            |
| `tests/test_profile.py`      | ✅     | `GET /profile/{username}`. Tests developer fields, repos, stats, 404, case insensitivity.                                                    |

### Frontend — styles

| File                             | Status | Notes                                                                                                                       |
| -------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------- |
| `frontend/src/styles/tokens.css` | ✅     | Full token system: typography, spacing, radii, shadows, z-index, light + dark mode colors, semantic aliases, heatmap cells. |
| `frontend/src/styles/global.css` | ✅     | Imports tokens, CSS reset, base styles, `.shimmer`, `.cursor` animations, `.sr-only`.                                       |

### Backend — workers (Phase 1 stubs, Phase 2 implementation)

| File                        | Status | Notes                                                                                                                                                                      |
| --------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/workers/__init__.py`   | ✅     | Package marker.                                                                                                                                                            |
| `app/workers/celery_app.py` | ✅     | Celery instance. Redis broker + backend. `task_acks_late=True`, `worker_prefetch_multiplier=1` for fair dispatch.                                                          |
| `app/workers/index_repo.py` | ✅     | `index_developer` + `index_single_repo` + `health_check` tasks. Phase 1: stubs that log and return. Phase 2: real fan-out logic replaces stubs. Worker starts cleanly now. |

### Still to build — Frontend (Phase 1)

- [ ] Vite scaffold: `npm create vite@latest . -- --template react-ts` + all npm installs
- [ ] `frontend/src/main.tsx` — import `global.css`, mount app, QueryClient, RouterProvider
- [ ] `frontend/src/router.ts` — TanStack Router routes: `/` and `/u/:username`
- [ ] `frontend/src/lib/api.ts` — typed fetch wrappers for all endpoints
- [ ] `frontend/src/store/profileStore.ts` — Zustand + immer
- [ ] `frontend/src/pages/Home.tsx` — search bar + submit
- [ ] `frontend/src/pages/Profile.tsx` — layout shell
- [ ] `frontend/src/components/profile/ProfileHeader/`
- [ ] `frontend/src/components/profile/StatsRow/`
- [ ] `frontend/src/components/profile/RepoCard/`
- [ ] `frontend/src/components/profile/RepoGrid/`
- [ ] `frontend/src/components/profile/LanguageBars/`
- [ ] `frontend/src/components/profile/ContributionStats/`
- [ ] `frontend/src/components/ui/` — Badge, Card, Skeleton shared primitives

---

## Decisions made (don't revisit)

| Decision                             | Reason                                                                                                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| React + Vite, NOT Next.js            | FastAPI is the backend. No SSR needed. Next.js adds complexity with no payoff here.                                                                                 |
| Radix UI + CSS Modules, NOT Tailwind | Full design control. CSS Modules scoped per component. Radix handles accessibility primitives.                                                                      |
| Build SVG components manually        | No Recharts/Chart.js. Shows deeper FE skill, keeps bundle small. D3 for math only, React renders SVG.                                                               |
| pgvector, NOT Pinecone               | Keep everything in Postgres. Simpler ops, no extra service.                                                                                                         |
| `ai/` separate from `backend/`       | AI layer has zero FastAPI knowledge. Importable, independently testable.                                                                                            |
| No BigQuery, No Storybook            | Out of scope. Component registry is its own design system story.                                                                                                    |
| All libraries free & open source     | No paid tiers. Every dependency is MIT/Apache licensed.                                                                                                             |
| `uv` NOT pip/requirements.txt        | 10–100x faster installs. `pyproject.toml` + `uv.lock` replaces `requirements.txt`. Docker builds go from minutes to seconds. Run `uv sync` locally for IDE support. |

---

## What makes it technically interesting

1. **AI decides what UI to render.** Claude returns structured JSON `{ type, text, data }`. The React frontend maps `type` to a component registry and renders it inline in the chat — like Claude.ai renders artifacts. The AI drives the UI, not the user.
2. **RAG on real code.** Code files are chunked by function, embedded via `text-embedding-3-small`, stored in pgvector. The assistant retrieves relevant chunks and cites them in answers.
3. **LangGraph analysis agent.** A multi-step agent with tools (GitHub API, code analyser) runs async via Celery, computing repo health scores, developer persona, and growth trajectory.
4. **Real-time via WebSocket.** Indexing progress pushed live. Frontend applies optimistic UI — profile skeleton renders immediately, data fills in as the agent completes.
5. **Virtual scroll.** TanStack Virtual for repo lists — handles 100+ repos without jank.
6. **Language fingerprint over time.** Tracks dominant stack per year — shows growth trajectory, not just a current snapshot.
7. **Shareable profile URLs.** `codesense.dev/u/torvalds` — every profile is a public, linkable URL. Virality built in.
8. **Developer comparison.** `/compare/:user1/:user2` — side-by-side analysis of two developers.
9. **Snapshot tracking.** Save profile snapshots over time — see how a developer evolves month over month.
10. **Lighthouse 95+.** Public profile pages optimised, documented before/after in README with public URL.

---

## Stack

### Backend

| Layer           | Tech                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------- |
| API             | FastAPI, Pydantic v2                                                                        |
| ORM             | SQLAlchemy 2.x (async) + Alembic                                                            |
| Workers         | Celery + Redis broker                                                                       |
| AI / RAG        | Anthropic API (`claude-sonnet-4-6`), LangGraph, LangSmith                                   |
| Embeddings      | `text-embedding-3-small` (OpenAI)                                                           |
| Database        | PostgreSQL 16 + pgvector extension                                                          |
| Cache / Queue   | Redis                                                                                       |
| Package manager | `uv` — replaces pip. 10–100x faster installs, lockfile via `uv.lock`, no `requirements.txt` |
| Observability   | Sentry, LangSmith traces, structured JSON logs                                              |
| Infra           | Docker + Docker Compose, GitHub Actions CI/CD                                               |

### Frontend — complete library list (all free & open source)

| Library                             | Purpose                                                                                     |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| `react` + `vite`                    | Core SPA + build tool                                                                       |
| `typescript`                        | Type safety throughout                                                                      |
| `@radix-ui/react-*`                 | Accessible unstyled primitives — Dialog, Tooltip, Tabs, ScrollArea, DropdownMenu            |
| CSS Modules                         | Scoped per-component styles — one `.module.css` per component, zero runtime cost            |
| `framer-motion`                     | Mount/unmount animations, layout transitions, skeleton → data swap                          |
| `lucide-react`                      | Icons — consistent, tree-shakeable, 1000+                                                   |
| `shiki`                             | Syntax highlighting (WASM, VS Code quality) for `CodePattern` component                     |
| `react-diff-view`                   | Unified/split diffs with line numbers for `CodePattern` component                           |
| `d3-scale` + `d3-shape`             | Math only — coordinate calculations for radar + heatmap. React renders SVG.                 |
| `@tanstack/react-router`            | Fully type-safe routing. Route params typed end to end.                                     |
| `@tanstack/react-query` v5          | Server state — fetching, caching, background refetch                                        |
| `@tanstack/react-virtual`           | Virtual scroll for repo grid (100+ repos)                                                   |
| `zustand` + `immer`                 | Client state — profile store, chat store, indexing state                                    |
| `ai` (Vercel AI SDK)                | `useChat` hook — SSE streaming, message history, abort. Free npm package, no Vercel needed. |
| `@microsoft/fetch-event-source`     | Production SSE — reconnection, POST support, visibility handling                            |
| `date-fns`                          | Date formatting — lightweight, tree-shakeable                                               |
| `clsx`                              | Conditional class name utility                                                              |
| `rollup-plugin-visualizer`          | Bundle analysis — `vite build` → `stats.html`                                               |
| `vitest` + `@testing-library/react` | Unit + component tests                                                                      |

---

## CSS architecture (CSS Modules)

Every component has its own `.module.css`. No global utility classes. No Tailwind.

```
CommitHeatmap/
├── CommitHeatmap.tsx
└── CommitHeatmap.module.css
```

```css
/* CommitHeatmap.module.css */
.grid {
  display: grid;
  gap: 3px;
}
.cell {
  border-radius: 2px;
  transition: transform 0.1s;
}
.cell:hover {
  transform: scale(1.3);
}
.cellLow {
  background: #9fe1cb;
}
.cellMid {
  background: #1d9e75;
}
.cellHigh {
  background: #085041;
}
```

```tsx
import styles from "./CommitHeatmap.module.css";
import { motion } from "framer-motion";

export function CommitHeatmap({ data, isStreaming }: Props) {
  return (
    <motion.div
      className={styles.grid}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {data.cells.map((cell, i) => (
        <div key={i} className={styles[`cell${cell.intensity}`]} />
      ))}
    </motion.div>
  );
}
```

**Global CSS** (`src/styles/global.css`) — only for CSS custom properties (design tokens), reset, and base body styles. Nothing else.

---

## Streaming UX patterns (the "Claude-like" feel)

Three patterns that must be implemented together:

### 1. Contextual thinking steps

Before streaming, push 2–3 specific steps via SSE `event: thinking_step`:

```
✓ Retrieving commit history across 34 repos
✓ Analysing day-of-week patterns
⟳ Generating insight…
```

Specific language ("34 repos"), not generic ("Loading…"). Steps check off as they complete.

### 2. Token-by-token text with blinking cursor

The `text` field streams character by character via `event: token`. A blinking CSS cursor sits at the end. Disappears on `event: done`.

```css
.cursor {
  display: inline-block;
  width: 2px;
  height: 14px;
  background: var(--color-text-primary);
  margin-left: 1px;
  animation: blink 1s step-end infinite;
  vertical-align: middle;
}
@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
```

### 3. Skeleton → progressive data fill

On `event: component_type` → mount the card with `framer-motion AnimatePresence` + shimmer skeleton. As `event: component_data` arrives → sections populate progressively. Heatmap cells appear left to right. Radar axes before polygon. Timeline entries top to bottom.

```tsx
function MessageStream({ message }: { message: StreamingMessage }) {
  const Component = message.type ? REGISTRY[message.type] : null;
  return (
    <AnimatePresence>
      {Component ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Component data={message.data} isStreaming={message.isStreaming} />
        </motion.div>
      ) : (
        <ComponentSkeleton />
      )}
    </AnimatePresence>
  );
}
```

---

## SSE event protocol (/query endpoint)

```
event: thinking_step   data: { "message": "Retrieving commits…", "done": false }
event: thinking_step   data: { "message": "Retrieving commits…", "done": true }
event: token           data: { "char": "R" }
event: component_type  data: { "type": "commit_heatmap" }
event: component_data  data: { ...partial data payload... }
event: done            data: {}
```

---

## The JSON contract

### AIMessage (ai/schemas/output.py)

```python
from typing import Literal
from pydantic import BaseModel

class AIMessage(BaseModel):
    type: Literal[
        "commit_heatmap", "skill_radar", "growth_timeline",
        "code_pattern", "repo_comparison", "developer_persona",
        "hire_recommendation", "text"
    ]
    text: str
    data: dict
```

### Frontend registry (registry.ts)

```ts
export const REGISTRY = {
  commit_heatmap: CommitHeatmap,
  skill_radar: SkillRadar,
  growth_timeline: GrowthTimeline,
  code_pattern: CodePattern,
  repo_comparison: RepoComparison,
  developer_persona: DeveloperPersona,
  hire_recommendation: HireRecommendation,
  text: TextMessage,
} as const;

export type ComponentType = keyof typeof REGISTRY;
```

---

## Key data flows

### Flow 1 — Indexing (async, Celery)

```
React POST /analyze
  → FastAPI creates IndexingJob → enqueues Celery task → Redis
  → Worker picks up → GitHub API (fetch all public repos)
  → Fan-out: celery.group — one sub-task per repo, all parallel
  → Each: fetch code → health_score → save Repo to Postgres
  → Phase 3+: Chunker → Embedder → pgvector
  → Phase 4+: LangGraph agent → persona + skill scores saved
  → Redis pub/sub → WebSocket push → frontend "ready"
```

### Flow 2 — RAG query (sync, SSE)

```
User question → POST /query
  → thinking_step SSE events during retrieval
  → Embed question → pgvector cosine similarity → top-k chunks
  → Prompt builder: system prompt + chunks
  → Anthropic API streaming → token events (typing effect)
  → component_type event → skeleton mounts
  → component_data events → component fills progressively
  → done event → cursor gone, steps all checked
  → LangSmith traces call
```

---

## Database models

```python
# Developer
id, github_username, display_name, avatar_url, bio,
ai_persona (text), skill_scores (jsonb),
index_status (pending/running/done/error), indexed_at, created_at

# Repo
id, developer_id (fk), github_id, name, description,
primary_language, all_languages (jsonb),
stars, forks, last_commit_at,
health_score (int 0-100), health_grade (A/B/C),
has_readme, has_tests, has_ci, has_docker, has_license,
commit_count, open_issues, closed_issues

# CodeChunk (pgvector)
id, repo_id (fk), file_path, chunk_index,
content (text), embedding (vector(1536)), token_count

# IndexingJob
id, developer_id (fk), status, repos_total, repos_done,
error_message, started_at, completed_at

# ProfileSnapshot
id, developer_id (fk), snapshot_data (jsonb), taken_at

# LLMCall
id, endpoint, model, tokens_in, tokens_out, cost_usd,
duration_ms, langsmith_run_id, created_at
```

---

## AI-rendered component types

| Type                  | Triggered by           | What it shows                              |
| --------------------- | ---------------------- | ------------------------------------------ |
| `commit_heatmap`      | "when do they ship?"   | GitHub-style SVG grid, weekend vs weekday  |
| `skill_radar`         | "how strong are they?" | SVG pentagon — BE/FE/AI/DevOps/Testing     |
| `growth_timeline`     | "how have they grown?" | Vertical milestone timeline, tech per year |
| `code_pattern`        | "how do they write X?" | Diff with shiki syntax highlighting        |
| `repo_comparison`     | "compare X and Y"      | Two-column scorecard                       |
| `developer_persona`   | "summarise this dev"   | AI paragraph + 4 trait bars                |
| `hire_recommendation` | "would you hire them?" | Verdict + reasoning + gaps                 |
| `text`                | everything else        | Plain answer with citation tags            |

---

## API endpoints

```
POST /analyze                        # submit username, start indexing
GET  /profile/:username              # full profile data
GET  /profile/:username/agent-trace  # LangSmith run URL
POST /query                          # RAG question → SSE stream
GET  /compare/:user1/:user2          # side-by-side profiles
POST /snapshot/:username             # save snapshot
GET  /snapshots/:username            # list snapshots
WS   /ws/:username                   # indexing progress
```

---

## Resume / interview signals

| Skill                          | How codesense covers it                                  |
| ------------------------------ | -------------------------------------------------------- |
| RAG                            | pgvector + retrieval + cited answers                     |
| Agents + tool calling          | LangGraph, conditional edges, GitHub + analyser tools    |
| Structured output → dynamic FE | JSON schema → component registry                         |
| WebSockets                     | Indexing progress via Redis pub/sub → WS                 |
| Celery                         | Fan-out — `celery.group`, one task per repo              |
| Virtual scroll                 | TanStack Virtual, 100+ repos                             |
| Optimistic UI                  | Skeleton first, data fills live                          |
| State management               | Zustand (UI) vs TanStack Query (server) — documented why |
| CSS architecture               | CSS Modules + design tokens, no Tailwind                 |
| Performance                    | Lighthouse 95+, before/after in README                   |
| Observability                  | Sentry, LangSmith, structured logs, cost dashboard       |
| System design                  | Fan-out pattern, Redis pub/sub bridge, SSE vs WS         |

---

## Environment variables

```
GITHUB_TOKEN=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/codesense
REDIS_URL=redis://redis:6379/0
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=codesense
SENTRY_DSN_BACKEND=
SENTRY_DSN_FRONTEND=
```

---

## Commands

```bash
make dev        # docker-compose up with hot reload
make migrate    # uv run alembic upgrade head
make test       # uv run pytest + vitest
make worker     # start Celery worker
make seed       # seed 3 real GitHub profiles
make install    # uv sync locally (for IDE support outside Docker)
make lock       # uv lock (after changing pyproject.toml)
make lint       # ruff check
make format     # ruff format
```

---

## Next steps (Phase 1 — frontend only)

Backend is complete and testable. All frontend work below.

### 1. Scaffold Vite + install deps

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install

# UI + animation
npm install @radix-ui/react-dialog @radix-ui/react-tooltip @radix-ui/react-tabs \
  @radix-ui/react-scroll-area @radix-ui/react-dropdown-menu \
  framer-motion lucide-react clsx date-fns

# State + routing + data fetching
npm install @tanstack/react-router @tanstack/react-query @tanstack/react-virtual \
  zustand immer

# Math for SVG charts (Phase 3 — install now, use later)
npm install d3-scale d3-shape

# Dev tools
npm install -D vitest @testing-library/react rollup-plugin-visualizer
```

### 2. `frontend/src/main.tsx`

Entry point. Import `global.css`. Mount `QueryClientProvider` + `RouterProvider`.

```tsx
import "./styles/global.css";
```

### 3. `frontend/src/router.ts`

TanStack Router with two routes: `/` → `Home`, `/u/$username` → `Profile`.
Note: TanStack Router uses `$param` syntax not `:param`.

### 4. `frontend/src/lib/api.ts`

Typed wrappers around `fetch`. Two functions to start:

- `analyzeUser(username: string)` → `POST /api/analyze`
- `getProfile(username: string)` → `GET /api/profile/{username}`

### 5. `frontend/src/store/profileStore.ts`

Zustand + immer. State shape:

```ts
{
  username: string | null;
  indexStatus: "idle" | "running" | "done" | "error";
  reposDone: number;
  reposTotal: number;
}
```

### 6. `frontend/src/pages/Home.tsx`

Search bar. On submit: call `analyzeUser()`, navigate to `/u/:username`.

### 7. `frontend/src/pages/Profile.tsx`

Layout shell. Uses `useProfile` (TanStack Query) to fetch `GET /api/profile/{username}`.
Shows loading skeleton while fetching, then mounts components.

### 8. Profile components (each gets its own folder + `.module.css`)

Build in this order — simplest first:

- `ui/Badge/` — health grade pill (A=green, B=amber, C=gray)
- `ui/Skeleton/` — shimmer placeholder, reused everywhere
- `profile/StatsRow/` — 5 stat cards from `stats` response field
- `profile/LanguageBars/` — iterate `language_percentages`, render bars
- `profile/RepoCard/` — name, description, grade badge, signal pills
- `profile/RepoGrid/` — CSS grid of RepoCards (virtual scroll in Phase 2)
- `profile/ProfileHeader/` — avatar, name, handle, AI persona (placeholder for now)
- `profile/ContributionStats/` — peak day, commit frequency from developer fields

### Done when

```
make dev && make migrate
open http://localhost:5173
type "torvalds" → see full profile with real GitHub data
```
