# PLAN.md — codesense build plan

> Sequenced to match the learning roadmap. Each phase builds on the last.
>
> Last updated: June 2026, after a status audit found Phase 4 had been skipped and mislabeled — see the correction note below before reading further.

---

## ⚠️ Correction note — read this first

A previous pass through this project built work under the label "Phase 4" that does not match this file. What actually got built was this file's **Phase 6** (Compare + Snapshot tracking) and most of **Phase 5** (Performance + deploy), done out of order, while **the real Phase 4 — the LangGraph analysis agent — was never started.**

Additionally, the Phase 3 RAG pipeline (`embedder.py`, `retriever.py`, `prompt_builder.py`, `streamer.py` per this plan) was implemented correctly in substance, but placed in a directory called `ai/agent/` and a file called `graph.py` with a function called `run_agent()` — borrowing Phase 4's vocabulary for Phase 3's work, before Phase 4's actual agent existed. If continuing this build in Claude Code, use `ai/rag/pipeline.py` and `run_pipeline()` for that Phase 3 work, and reserve `ai/agent/` exclusively for the real Phase 4 build below.

Status markers below (✅ / ❌ / ⚠️) reflect actual reality, not aspiration.

---

## Where you are right now

**Completed from roadmap (pre-project):**

- FastAPI basics — blog site with full CRUD
- Redis rate limiting
- JWT auth
- Docker + Docker Compose
- SQLAlchemy + Alembic

**Completed in this project:**

- ✅ Phase 1 — Foundation
- ✅ Phase 2 — Celery + WebSockets + real-time
- ✅ Phase 3 — RAG assistant + streaming component rendering (file naming note: `ai/agent/graph.py` should be `ai/rag/pipeline.py` — see note above)
- ✅ Phase 4 — LangGraph analysis agent (complete)
- ⚠️ Phase 5 — Performance + observability + deploy (performance + deploy configs done; observability not built)
- ⚠️ Phase 6 — Compare + Snapshot tracking (compare ✅ done, snapshots ✅ done basic, history/diff view not built)

**Starting point now:** Phase 5 observability (Sentry, structured logging, LLMCall cost tracking) — the last meaningful code gap.

---

## Phase 1 — Foundation ✅ COMPLETE

**Goal:** Data flows end to end. GitHub username in → profile page out. No AI yet.

All backend and frontend tasks from the original Phase 1 checklist are done. Profile pages render real GitHub data, repos get A/B/C health grades, language bars work. See CLAUDE.md's Phase 1 section for the full file-by-file record.

---

## Phase 2 — Celery + WebSockets + real-time ✅ COMPLETE

**Goal:** Indexing happens in the background. Frontend feels live.

Fan-out via `celery.group`, Redis pub/sub bridges to a WebSocket, frontend shows live progress. One real bug hit and fixed along the way: `CORSMiddleware` doesn't cover WebSocket upgrades, so the `/ws/{username}` endpoint needed a manual origin check. See CLAUDE.md's Phase 2 section.

---

## Phase 3 — RAG assistant + streaming component rendering ✅ COMPLETE (naming needs correction)

**Goal:** The core AI feature. User asks a question → right component streams back with Claude-like feel.

All of this is built and working:

- Chunking by function/class boundary, local embedding via `fastembed` (swapped from the original `text-embedding-3-small` plan — see CLAUDE.md's embedding decision table for why), pgvector cosine retrieval
- SSE streaming with `thinking_step` → `token` → `component` → `done` events
- 7 AI-rendered components with a frontend registry (`CommitHeatmap`, `SkillRadar`, `GrowthTimeline`, `RepoComparison`, `DeveloperPersona`, `HireRecommendation`, `TextMessage` — `CodePattern` from the original plan was not built, no shiki/react-diff-view component exists yet)
- Generation model swapped from Anthropic to Groq (`llama-3.3-70b-versatile`) — free tier, OpenAI-compatible API, see CLAUDE.md's generation model decision table

**Action item if continuing in Claude Code:** rename `ai/agent/prompts.py` → `ai/rag/prompts.py`, `ai/agent/graph.py` → `ai/rag/pipeline.py`, and the `run_agent()` function → `run_pipeline()`. This is cosmetic — no behavior changes — but matters because Phase 4 below needs `ai/agent/` for real agent code, and the current naming would collide/confuse.

**Not built from the original Phase 3 scope:**

- `CodePattern` component (shiki + react-diff-view) — skipped, no code currently triggers this component type
- LangSmith tracing on every LLM call — `LANGCHAIN_*` env vars exist but nothing actually calls LangSmith yet
- Rate limiting on `/query` (20 req/min per IP via Redis) — not implemented, flagged as an open risk for a public deploy

---

## Phase 4 — LangGraph analysis agent ✅ COMPLETE

**Goal:** Deep multi-step AI analysis. A real agent replaces heuristic health scoring and the Phase 3 pipeline's per-question guesswork.

### What was built

- [x] `app/ai/agent/tools.py` — `fetch_code_samples()`, `analyse_patterns()`, `compute_growth()` (pure Python, no LLM)
- [x] `app/ai/agent/nodes.py` — 4 sync node functions: `fetch_node`, `analyse_node`, `persona_node`, `score_node`
- [x] `app/ai/agent/graph.py` — real `StateGraph` (4 nodes, conditional re-fetch edge if < 5 samples on first attempt)
- [x] `app/workers/analysis_agent.py` — `analyse_developer` Celery task; loads repos, calls `run_analysis()`, persists results
- [x] `on_indexing_complete` triggers `analyse_developer.delay(developer_id)` after snapshot
- [x] `GET /api/profile/{username}/agent-trace` — returns `has_analysis`, `skill_scores`, `ai_persona`, LangSmith URL
- [x] `app/ai/rag/pipeline.py` + `app/ai/rag/prompts.py` — Phase 3 pipeline moved here from `ai/agent/` to free directory for real agent
- [x] `query.py` import updated to `run_pipeline`; `developer_dict` includes `ai_persona` + `skill_scores`
- [x] `build_developer_context()` in `rag/prompts.py` surfaces pre-computed persona/scores into the RAG prompt
- [x] `Profile.tsx` shows "AI analyzed" badge in nav when `skill_scores` are present

### Notes

- All agent nodes are sync (`def`, not `async def`) — LangGraph invoked via `graph.invoke()` inside Celery
- `analysis_graph` compiled at module import time, reused across task invocations
- Groq heuristic fallback in `score_node` so the task never hard-fails even if the API is unavailable
- LangSmith tracing is automatic when `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` is set — no extra code needed
- `SkillRadar` and `DeveloperPersona` in chat now receive pre-computed scores/persona via the RAG prompt context; the Phase 3 system prompt prefers them when present

---

## Phase 5 — Performance + observability + deploy ⚠️ PARTIALLY COMPLETE

**Goal:** Production-ready. Public URL. Lighthouse 95+. Observable.

### Performance tasks

- [x] `React.lazy()` + `Suspense` for all `ai-components/` — done via `registry.ts` since Phase 3
- [x] Lazy-load `ChatPanel` — only mounts after profile data loads
- [ ] Defer WebSocket connection until after first paint — not done, `useIndexingProgress` connects immediately on mount
- [x] Preconnect hints added (`avatars.dicebear.com`, `github.com`, dns-prefetch `api.groq.com`)
- [x] OG meta tags per profile (`useProfileMeta.ts`, vanilla DOM API)
- [ ] Measure Lighthouse on `/u/:username` — manual step, not done, needs a deployed URL
- [ ] `rollup-plugin-visualizer` → `vite build` → inspect `stats.html` for heavy deps — not run yet
- [x] Pure SVG components, no chart library weight — confirmed, all 7 AI components hand-built
- [ ] Document before/after in README with screenshots + live URL — README has TODO placeholders, blocked on the Lighthouse run above

### Observability tasks ❌ NOT BUILT

- [ ] Sentry: Vite plugin (frontend) + FastAPI middleware (backend) — `SENTRY_DSN_*` env vars exist in `.env.example` but nothing reads them beyond a prod-only init stub from Phase 1
- [ ] Structured JSON logging — current logging is ad hoc `logger.info(f"...")` calls, not structured `{ method, path, status, duration_ms }` records
- [ ] `LLMCall` table — model has existed since the Phase 1 migration, nothing writes to it. Every Groq call in the Phase 3 pipeline should log a row here (model, tokens_in, tokens_out, cost_usd, duration_ms)
- [ ] Admin page `/admin` — LLMCall table, total cost, error rate, p95 latency — not built

### Deploy tasks ⚠️ CONFIGS DONE, NOT ACTUALLY DEPLOYED

- [x] GitHub Actions CI — lint + build on PR/push (`deploy/.github/workflows/ci.yml`). Deploy-on-merge intentionally left to Railway/Vercel's native GitHub integration, no custom Action step for it
- [x] Deploy configs written: `deploy/railway.json`, `deploy/Procfile` (web + worker processes), `deploy/vercel.json`, `deploy/.env.production.example`
- [ ] Actually deploy to Railway/Vercel — manual step, not done, needs account signup and clicking through
- [ ] Custom domain `codesense.dev` — unconfirmed, referenced throughout CLAUDE.md as aspirational, ownership not verified
- [ ] SSL — handled automatically by Railway/Vercel once deployed, no action needed beyond deploying

### Done when

`codesense.dev/u/torvalds` loads under 1.5s. Lighthouse 95+. Sentry live. LangSmith tracing. CI green.

**Current state:** CI is green. Nothing else in this "done when" checklist is verifiable yet — no live URL exists to measure Lighthouse against, and Sentry/LangSmith were never wired up.

---

## Phase 6 — Compare + Snapshot tracking ⚠️ MOSTLY COMPLETE

Build these when the core profile is stable. Both add real value and virality.

### Compare (`/compare/:user1/:user2`) ✅ DONE

- [x] `app/api/routes/compare.py` — `GET /api/compare/{user1}/{user2}` returns `{ left: ProfileResponse, right: ProfileResponse }`
- [x] `src/pages/Compare.tsx` — side-by-side layout, skeleton → data
- [x] `src/components/compare/ComparisonHeader/` — two avatar+name cards with "vs" divider
- [x] `src/components/compare/ComparisonStats/` — repos / avg health / A-grade count, bars race from center, winner highlighted
- [x] `src/components/profile/CompareEntry/` — "Compare with…" pill on Profile nav → navigates to `/compare/:username/:other`
- [x] `/compare/$user1/$user2` route registered in `src/router.ts`
- [x] `compareProfiles()` in `src/lib/api_compare_addition.ts`
- [x] `repo_comparison` AI component type already in registry

### Snapshot tracking ✅ DONE (basic)

- [x] `app/api/routes/snapshot.py` — `POST /api/snapshot/{username}` + `GET /api/snapshots/{username}`
- [x] Auto-snapshot in `on_indexing_complete` via `_create_snapshot_sync()` (sync session, avoids async/sync mismatch)
- [x] Staleness check on `/analyze` — skips re-indexing if `indexed_at` < 1 hour old, `?force=true` to bypass
- [x] `src/components/profile/SnapshotInfo/` — "Last indexed Xh ago" + Re-index button
- [ ] Snapshot history timeline on profile — not built
- [ ] Diff view between two snapshots ("how has this developer changed since March?") — not in scope for initial build

---

## Shortcuts to avoid

| Temptation                                  | Why to resist                                                                                                                                                                                                          |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Adding Next.js                              | FastAPI is your backend. No SSR needed. Decision made.                                                                                                                                                                 |
| Tailwind CSS                                | Decision made. CSS Modules gives you full control and cleaner code.                                                                                                                                                    |
| Recharts / Chart.js                         | Build SVG manually. Shows FE depth. Keeps bundle small. Held to — all 7 AI components are hand-built SVG/HTML.                                                                                                         |
| External chart lib for radar/heatmap        | D3 math + React SVG is the correct pattern for custom visuals. Held to.                                                                                                                                                |
| Skipping CSS Modules per-component          | Global styles create specificity hell. Every component gets its own `.module.css`. Held to.                                                                                                                            |
| Using pip / requirements.txt                | Decision made. `uv` + `pyproject.toml` is the standard. Held to.                                                                                                                                                       |
| Building AI before foundation               | Debug order: FastAPI → Celery → WebSocket → then AI. Held to — phases 1-3 went in order.                                                                                                                               |
| Generic spinner instead of thinking steps   | Thinking steps are the feel difference. Held to — `ThinkingSteps` component does this.                                                                                                                                 |
| Over-engineering the agent                  | 4 nodes, linear flow. Add complexity when needed. Not yet applicable — agent doesn't exist yet.                                                                                                                        |
| Claiming Phase 4 work is done when it isn't | This is exactly what happened — work got labeled "Phase 4" that was actually Phases 5/6, while real Phase 4 was skipped silently. Always check file/section names against this plan before marking something complete. |

---

## Interview talking points (per phase)

**After Phase 1:**

> "I built a GitHub repo health scorer — checks README presence, test file patterns, CI config, Docker, license, and commit recency. Every repo gets an A/B/C grade. Pure signal detection, no AI."

**After Phase 2:**

> "Indexing fans out with Celery — `celery.group` runs one task per repo all in parallel. Celery publishes progress to Redis pub/sub. The WebSocket subscribes and pushes live to the frontend."

**After Phase 3:**

> "The LLM returns structured JSON — a type field and a data payload. The frontend has a component registry that maps type to a React component and renders it inline, streaming. The AI decides what UI to show. Same pattern Claude.ai uses for artifacts."

Honest framing: this is a RAG pipeline (retrieve → prompt → stream → parse), not an agent. Don't claim agent/tool-calling here — that's Phase 4, and it's fine to say so directly.

**After Phase 4 (not yet earned — don't use this talking point until Phase 4 actually ships):**

> "The analysis agent runs a 4-node LangGraph graph — fetch, analyse, persona, score. Each node completion fires a WebSocket event. Every run is traced in LangSmith."

**After Phase 5 (partially earned):**

What's true today: "Indexing fans out across CPU-bound workers with optimistic UI — skeleton renders immediately." What's not yet true: any specific Lighthouse number, any observability claim (no Sentry, no cost dashboard exist yet) — don't cite these until Phase 5's observability section and the actual Lighthouse run are done.

**After Phase 6:**

> "Every profile has a shareable URL. The compare page puts two developers side by side with a shared stats comparison. Profiles snapshot automatically after each index run, with a staleness check to avoid wasting free-tier API quota on repeated re-indexing."

Accurate, but don't claim the snapshot diff/timeline view, since it isn't built.
