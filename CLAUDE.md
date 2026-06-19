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

## What's been built (Phase 1 — COMPLETE ✅)

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

| File                      | Status | Notes                                                                                                                                                                                                                                   |
| ------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/models/__init__.py`  | ✅     | Imports all models — required for Alembic autogenerate discovery.                                                                                                                                                                       |
| `app/models/base.py`      | ✅     | `DeclarativeBase` + `utcnow()` helper.                                                                                                                                                                                                  |
| `app/models/profile.py`   | ✅     | `Developer`, `Repo`, `IndexingJob`, `ProfileSnapshot` + `IndexStatus`, `HealthGrade` enums.                                                                                                                                             |
| `app/models/embedding.py` | ✅     | `CodeChunk`. `embedding` col is plain `Text` — conditional `if VECTOR_AVAILABLE` inside class body was removed (broke SQLAlchemy declarative). Phase 3 migration ALTERs it to `vector(384)` (fastembed `bge-small-en-v1.5` output dim). |
| `app/models/llm_call.py`  | ✅     | Cost tracking — model, tokens_in/out, cost_usd, duration_ms, langsmith_run_id.                                                                                                                                                          |

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
| `tests/test_health_score.py` | ✅     | 20 unit tests. Every scoring branch + edge cases.                                                                                            |
| `tests/test_analyze.py`      | ✅     | `POST /analyze` with mocked GitHub API. Tests happy path, 404, idempotent upsert.                                                            |
| `tests/test_profile.py`      | ✅     | `GET /profile/{username}`. Tests developer fields, repos, stats, 404, case insensitivity.                                                    |

### Backend — workers (stubs — Phase 2 implements these)

| File                        | Status | Notes                                                                                                                                          |
| --------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/workers/__init__.py`   | ✅     | Package marker.                                                                                                                                |
| `app/workers/celery_app.py` | ✅     | Celery instance. Redis broker + backend. `task_acks_late=True`, `worker_prefetch_multiplier=1` for fair dispatch.                              |
| `app/workers/index_repo.py` | ✅     | `index_developer` + `index_single_repo` + `health_check` tasks. Currently stubs that log and return. Phase 2 replaces with real fan-out logic. |

### Frontend — Phase 1 COMPLETE ✅

| File                                                    | Status | Notes                                                                                                                                                                                             |
| ------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frontend/package.json`                                 | ✅     | All deps pinned. React 18, Vite 5, TanStack Router/Query/Virtual, Zustand, Framer Motion, Radix UI, Lucide.                                                                                       |
| `frontend/vite.config.ts`                               | ✅     | React plugin, `@` path alias, proxy `/api` → `localhost:8000`, `/ws` → WS.                                                                                                                        |
| `frontend/tsconfig.json`                                | ✅     | Strict mode, `bundler` moduleResolution, path aliases.                                                                                                                                            |
| `frontend/index.html`                                   | ✅     | Entry point, mounts `#root`.                                                                                                                                                                      |
| `frontend/src/styles/tokens.css`                        | ✅     | Full token system: typography, spacing, radii, shadows, z-index, dark mode colors, grade colors, heatmap cells.                                                                                   |
| `frontend/src/styles/global.css`                        | ✅     | Imports tokens, CSS reset, base styles, `.shimmer`, `.cursor` animations, `.sr-only`, scrollbar.                                                                                                  |
| `frontend/src/lib/types.ts`                             | ✅     | All TypeScript types matching backend schemas exactly: `DeveloperResponse`, `RepoResponse`, `ProfileStatsResponse`, `ProfileResponse`, `AnalyzeResponse`, `WsProgressMessage`, `StreamComponent`. |
| `frontend/src/lib/api.ts`                               | ✅     | Typed fetch wrappers: `analyzeUser()`, `getProfile()`, `compareProfiles()`. `ApiError` class with status code.                                                                                    |
| `frontend/src/lib/utils.ts`                             | ✅     | `getLangColor()`, `getGradeColor()`, `getGradeBg()`, `formatNumber()`, `formatPercent()`, `timeAgo()`, `cx()`.                                                                                    |
| `frontend/src/store/profileStore.ts`                    | ✅     | Zustand + immer. State: `username`, `indexStatus`, `reposDone`, `reposTotal`, `jobId`, `error`.                                                                                                   |
| `frontend/src/router.ts`                                | ✅     | TanStack Router. Routes: `/` → `Home`, `/u/$username` → `Profile`. Type-registered.                                                                                                               |
| `frontend/src/main.tsx`                                 | ✅     | `QueryClientProvider` (staleTime 5min, gcTime 30min) + `RouterProvider`. Imports `global.css`.                                                                                                    |
| `frontend/src/pages/Home.tsx` + `Home.module.css`       | ✅     | Search bar, spinner, error state, 5 example username buttons. `analyzeUser()` → navigate to profile.                                                                                              |
| `frontend/src/pages/Profile.tsx` + `Profile.module.css` | ✅     | Sticky nav, skeleton → data swap via `AnimatePresence`. Sidebar (LanguageBars + ContributionStats) + main (RepoGrid) layout. Error + retry state.                                                 |
| `frontend/src/components/ui/Badge/`                     | ✅     | Health grade pill. A=green, B=amber, C=gray, D/F=red. Sizes: sm/md/lg.                                                                                                                            |
| `frontend/src/components/ui/Skeleton/`                  | ✅     | Base shimmer + `ProfileHeaderSkeleton`, `StatsRowSkeleton`, `RepoCardSkeleton`, `RepoGridSkeleton`.                                                                                               |
| `frontend/src/components/profile/ProfileHeader/`        | ✅     | Avatar, display name, @handle (links to GitHub), bio, AI persona (italic, accent border).                                                                                                         |
| `frontend/src/components/profile/StatsRow/`             | ✅     | 5 animated stat cards: repos, stars, forks, commits, avg health. Icons from lucide-react.                                                                                                         |
| `frontend/src/components/profile/LanguageBars/`         | ✅     | Summary strip + legend. Animated fill bars via framer-motion. Top 8 languages.                                                                                                                    |
| `frontend/src/components/profile/RepoCard/`             | ✅     | Name, description, grade Badge, signal pills (README/Tests/CI/Docker/License), footer meta (lang dot, stars, forks, commits, last commit).                                                        |
| `frontend/src/components/profile/RepoGrid/`             | ✅     | Sort controls (Health/Stars/Commits/Recent) + responsive CSS grid of RepoCards.                                                                                                                   |
| `frontend/src/components/profile/ContributionStats/`    | ✅     | Peak commit day, commit frequency/wk, repos-with-tests cards.                                                                                                                                     |

---

## Decisions made (don't revisit)

| Decision                                    | Reason                                                                                                                                                                                                                                                               |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| React + Vite, NOT Next.js                   | FastAPI is the backend. No SSR needed. Next.js adds complexity with no payoff here.                                                                                                                                                                                  |
| Radix UI + CSS Modules, NOT Tailwind        | Full design control. CSS Modules scoped per component. Radix handles accessibility primitives.                                                                                                                                                                       |
| Build SVG components manually               | No Recharts/Chart.js. Shows deeper FE skill, keeps bundle small. D3 for math only, React renders SVG.                                                                                                                                                                |
| pgvector, NOT Pinecone                      | Keep everything in Postgres. Simpler ops, no extra service.                                                                                                                                                                                                          |
| `ai/` separate from `backend/`              | AI layer has zero FastAPI knowledge. Importable, independently testable.                                                                                                                                                                                             |
| No BigQuery, No Storybook                   | Out of scope. Component registry is its own design system story.                                                                                                                                                                                                     |
| All libraries free & open source            | No paid tiers. Every dependency is MIT/Apache licensed.                                                                                                                                                                                                              |
| `uv` NOT pip/requirements.txt               | 10–100x faster installs. `pyproject.toml` + `uv.lock` replaces `requirements.txt`. Docker builds go from minutes to seconds. Run `uv sync` locally for IDE support.                                                                                                  |
| No conditional columns in SQLAlchemy models | `if VECTOR_AVAILABLE: embedding = ...` inside a class body breaks SQLAlchemy declarative mapping. Always define columns unconditionally — use `Text` as placeholder, ALTER in a migration later. Fixed in `embedding.py`.                                            |
| No tests until project is done              | Skipping vitest and @testing-library/react until all phases are built. Tests will be added at the end.                                                                                                                                                               |
| `fastembed` NOT OpenAI for embeddings       | Runs locally on M4 CPU (~200MB RAM, ~0.5s/100 chunks). Free, no API key, no data leaving the machine. `BAAI/bge-small-en-v1.5` produces 384-dim vectors — excellent for code similarity. Removes OpenAI as a dependency entirely.                                    |
| Groq NOT Anthropic/OpenAI for generation    | Free tier: 14,400 req/day, 6000 tokens/min. `llama-3.3-70b-versatile` is genuinely capable at code reasoning. OpenAI-compatible API — one line to swap to any other provider later. LPU inference is 10x faster than GPU, streaming feels instant. Zero cost in dev. |

---

## What makes it technically interesting

1. **AI decides what UI to render.** The LLM (Groq `llama-3.3-70b`) returns structured JSON `{ type, text, data }`. The React frontend maps `type` to a component registry and renders it inline in the chat — like Claude.ai renders artifacts. The AI drives the UI, not the user.
2. **RAG on real code.** Code files are chunked by function, embedded locally via `fastembed` (`BAAI/bge-small-en-v1.5`, runs on M4 CPU, free), stored in pgvector. The assistant retrieves relevant chunks and cites them in answers.
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

| Layer           | Tech                                                                                                                       |
| --------------- | -------------------------------------------------------------------------------------------------------------------------- |
| API             | FastAPI, Pydantic v2                                                                                                       |
| ORM             | SQLAlchemy 2.x (async) + Alembic                                                                                           |
| Workers         | Celery + Redis broker                                                                                                      |
| AI / RAG        | Groq API (`llama-3.3-70b-versatile`) — free tier, OpenAI-compatible, 10x faster than GPU inference. LangSmith for tracing. |
| Embeddings      | `fastembed` — runs locally, no API key, no cost. Model: `BAAI/bge-small-en-v1.5` (130MB, 384-dim, CPU-friendly on M4)      |
| Database        | PostgreSQL 16 + pgvector extension                                                                                         |
| Cache / Queue   | Redis                                                                                                                      |
| Package manager | `uv` — replaces pip. 10–100x faster installs, lockfile via `uv.lock`, no `requirements.txt`                                |
| Observability   | Sentry, LangSmith traces, structured JSON logs                                                                             |
| Infra           | Docker + Docker Compose, GitHub Actions CI/CD                                                                              |

### Frontend — complete library list (all free & open source)

| Library                         | Purpose                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------- |
| `react` + `vite`                | Core SPA + build tool                                                                       |
| `typescript`                    | Type safety throughout                                                                      |
| `@radix-ui/react-*`             | Accessible unstyled primitives — Dialog, Tooltip, Tabs, ScrollArea, DropdownMenu            |
| CSS Modules                     | Scoped per-component styles — one `.module.css` per component, zero runtime cost            |
| `framer-motion`                 | Mount/unmount animations, layout transitions, skeleton → data swap                          |
| `lucide-react`                  | Icons — consistent, tree-shakeable, 1000+                                                   |
| `shiki`                         | Syntax highlighting (WASM, VS Code quality) for `CodePattern` component                     |
| `react-diff-view`               | Unified/split diffs with line numbers for `CodePattern` component                           |
| `d3-scale` + `d3-shape`         | Math only — coordinate calculations for radar + heatmap. React renders SVG.                 |
| `@tanstack/react-router`        | Fully type-safe routing. Route params typed end to end.                                     |
| `@tanstack/react-query` v5      | Server state — fetching, caching, background refetch                                        |
| `@tanstack/react-virtual`       | Virtual scroll for repo grid (100+ repos)                                                   |
| `zustand` + `immer`             | Client state — profile store, chat store, indexing state                                    |
| `ai` (Vercel AI SDK)            | `useChat` hook — SSE streaming, message history, abort. Free npm package, no Vercel needed. |
| `@microsoft/fetch-event-source` | Production SSE — reconnection, POST support, visibility handling                            |
| `date-fns`                      | Date formatting — lightweight, tree-shakeable                                               |
| `clsx`                          | Conditional class name utility                                                              |
| `rollup-plugin-visualizer`      | Bundle analysis — `vite build` → `stats.html`                                               |

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

```bash
# ── Required now (Phase 2) ──────────────────────────────

# github.com → Settings → Developer settings → Personal access tokens
# → Tokens (classic) → Generate → scope: public_repo only. Free, 5000 req/hr.
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Generate locally — never reuse between projects:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-random-64-char-hex-string

# ── Local Docker services (no signup needed) ────────────

DATABASE_URL=postgresql+asyncpg://codesense:codesense@postgres:5432/codesense
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ── App ─────────────────────────────────────────────────

ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173

# ── Phase 3 — AI (leave blank until then) ───────────────

# console.groq.com → Sign up free → API Keys → Create.
# Free tier: 14,400 req/day, 6000 tokens/min. No credit card needed.
# Model: llama-3.3-70b-versatile
GROQ_API_KEY=

# No OpenAI key needed — embeddings run locally via fastembed (BAAI/bge-small-en-v1.5).
# Model downloads once (~130MB) to ~/.cache/fastembed/ on first worker start.

# smith.langchain.com → Sign up (free) → Settings → API Keys.
# Free tier: unlimited traces for personal projects.
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=codesense

# ── Production only (leave blank in dev) ────────────────

# sentry.io → Sign up (free, 5000 errors/month) → New Project
# → FastAPI → copy DSN. Create second project for React.
# Only initialises when ENVIRONMENT=production AND DSN is set.
SENTRY_DSN_BACKEND=
SENTRY_DSN_FRONTEND=
```

---

## Commands

```bash
make dev        # docker-compose up with hot reload
make migrate    # uv run alembic upgrade head
make worker     # start Celery worker
make seed       # seed 3 real GitHub profiles
make install    # uv sync locally (for IDE support outside Docker)
make lock       # uv lock (after changing pyproject.toml)
make lint       # ruff check
make format     # ruff format
```

---

## Phase 2 — Real-time indexing (COMPLETE ✅)

### Backend — new/replaced files

| File                          | Status | Notes                                                                                                                                                        |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `app/workers/index_repo.py`   | ✅     | Real fan-out: `index_developer` fetches repos → `celery.group` of `index_single_repo` per repo → chord `on_indexing_complete`.                               |
| `app/workers/redis_client.py` | ✅     | Sync Redis client (`redis.from_url`) for Celery workers. Used to `PUBLISH` progress events.                                                                  |
| `app/db/sync_session.py`      | ✅     | Sync SQLAlchemy session (`SyncSessionLocal`) for workers. Converts `asyncpg://` URL to `psycopg2://`.                                                        |
| `app/services/github_sync.py` | ✅     | Sync versions of GitHub API methods to paste into `GitHubService`: `get_repos_sync`, `get_languages_sync`, `get_commit_count_sync`, `get_repo_signals_sync`. |
| `app/api/routes/analyze.py`   | ✅     | Phase 2 version — calls `index_developer.delay()` and returns immediately. Synchronous indexing loop removed.                                                |
| `app/api/routes/ws.py`        | ✅     | `WS /ws/{username}` — subscribes to Redis pub/sub channel, streams events to client, closes on `done`/`error`.                                               |
| `app/main_patch.py`           | ✅     | Instructions for registering WS router in `app/main.py`.                                                                                                     |

**One manual step in `app/main.py`:**

```python
from app.api.routes import ws as ws_routes
app.include_router(ws_routes.router)   # no prefix — path is /ws/{username}
```

### Frontend — new/updated files

| File                                                | Status | Notes                                                                                                            |
| --------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| `frontend/src/hooks/useIndexingProgress.ts`         | ✅     | Opens WS to `/ws/{username}` while status is pending/running. Drives Zustand store. Calls `onDone()` to refetch. |
| `frontend/src/components/profile/IndexingProgress/` | ✅     | Banner with spinner → animated progress bar → check icon on done. Auto-hides after completion.                   |
| `frontend/src/store/profileStore.ts`                | ✅     | Updated — adds `"idle"` status, `error` field. Replace Phase 1 version.                                          |
| `frontend/src/lib/types.ts`                         | ✅     | Updated — `WsProgressMessage` now has `"started"` type + `repo` field. Replace Phase 1 version.                  |
| `frontend/src/pages/Profile.tsx`                    | ✅     | Updated — wires `useIndexingProgress`, renders `<IndexingProgress />`, polls as fallback during indexing.        |

### Done when

```
make dev && make migrate && make worker
open http://localhost:5173
type "torvalds" → progress bar fills live as repos index → profile renders
```

---

## Next steps — Phase 3 (AI / RAG layer)

### Embedding decision (locked)

**No OpenAI.** Embeddings run locally via `fastembed` — free, offline, no API key.

|             | fastembed (chosen)         | OpenAI text-embedding-3-small |
| ----------- | -------------------------- | ----------------------------- |
| Cost        | Free                       | ~$0.02/M tokens               |
| Latency     | ~0.5s/100 chunks on M4 CPU | ~200ms API round-trip         |
| Privacy     | Stays on your machine      | Sent to OpenAI servers        |
| Setup       | `pip install fastembed`    | API key + account             |
| Vector dims | 384                        | 1536                          |
| Quality     | Excellent for code         | Marginally better             |

Model: `BAAI/bge-small-en-v1.5` (~130MB, downloads once to `~/.cache/fastembed/`).

**Docker volume to persist the cache (add to `docker-compose.yml`):**

```yaml
worker:
  volumes:
    - fastembed_cache:/root/.cache/fastembed

volumes:
  fastembed_cache:
```

### Generation model decision (locked)

**Groq, not Anthropic or OpenAI.** Free tier is real and sufficient.

|                    | Groq (chosen)           | Anthropic Claude  | OpenAI GPT-4o |
| ------------------ | ----------------------- | ----------------- | ------------- |
| Cost               | Free (14.4k req/day)    | Pay-per-token     | Pay-per-token |
| Model              | llama-3.3-70b-versatile | claude-sonnet-4-6 | gpt-4o        |
| API style          | OpenAI-compatible ✅    | Custom SDK        | OpenAI        |
| Speed              | 🏆 LPU, ~10x faster     | Fast              | Fast          |
| Code reasoning     | Strong                  | Excellent         | Excellent     |
| Swap to paid later | 1 line change           | SDK change        | 1 line change |

```python
from openai import OpenAI  # same package, different base_url

client = OpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)
```

### What to build

**`ai/` directory** (separate from `backend/` — zero FastAPI knowledge):

```
ai/
├── __init__.py
├── schemas/
│   └── output.py          # AIMessage pydantic model
├── agent/
│   ├── __init__.py
│   ├── graph.py            # LangGraph StateGraph definition
│   ├── nodes.py            # retrieve, generate, format_component nodes
│   ├── tools.py            # GitHub tool + code analyser tool
│   └── prompts.py          # system prompt templates
├── rag/
│   ├── __init__.py
│   ├── chunker.py          # split code files by function/class boundary
│   ├── embedder.py         # fastembed BAAI/bge-small-en-v1.5 — local, free
│   └── retriever.py        # pgvector cosine similarity search (vector(384))
└── cost_tracker.py         # no-op in dev (Groq is free); logs token usage only
```

**Backend additions:**

- `app/api/routes/query.py` — `POST /query` SSE endpoint. Accepts `{ username, question }`, streams events per the SSE protocol.
- `app/api/routes/compare.py` — `GET /compare/:user1/:user2`.
- `app/workers/embed_repo.py` — Celery task: chunker → fastembed → pgvector. Triggered after `index_single_repo` completes.
- Migration `002_vector_column.py`: ALTER `code_chunks.embedding` from `TEXT` to `vector(384)`.

**Frontend additions:**

```
src/
├── hooks/
│   └── useChat.ts                    # SSE streaming, message history, abort
├── store/
│   └── chatStore.ts                  # Zustand: messages, isStreaming, thinkingSteps
├── components/
│   ├── chat/
│   │   ├── ChatPanel/                # slide-in panel, input bar, message list
│   │   ├── ThinkingSteps/            # ✓ checked steps with timing
│   │   └── MessageStream/            # text cursor + component registry switch
│   └── ai-components/
│       ├── CommitHeatmap/            # SVG GitHub-style grid
│       ├── SkillRadar/               # SVG pentagon
│       ├── GrowthTimeline/           # vertical milestone timeline
│       ├── CodePattern/              # shiki + react-diff-view
│       ├── RepoComparison/           # two-column scorecard
│       ├── DeveloperPersona/         # paragraph + 4 trait bars
│       └── HireRecommendation/       # verdict card
└── lib/
    └── registry.ts                   # ComponentType → component map
```

### SSE event protocol

```
event: thinking_step   data: { "message": "Retrieving commit history…", "done": false }
event: thinking_step   data: { "message": "Retrieving commit history…", "done": true }
event: token           data: { "char": "T" }
event: component_type  data: { "type": "commit_heatmap" }
event: component_data  data: { ...partial payload... }
event: done            data: {}
```

### Done when

```
open http://localhost:5173/u/torvalds
# click "Ask anything" → "when does torvalds ship code?"
# → thinking steps appear → text streams → CommitHeatmap renders
```
