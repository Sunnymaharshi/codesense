# codesense — local development
#
# Quickstart:
#   1. make setup        (first time only — copies .env, installs frontend deps)
#   2. Edit .env and fill in GITHUB_TOKEN and GROQ_API_KEY
#   3. make dev          (starts postgres + redis + api + worker in Docker)
#   4. make migrate      (run once after first `make dev`)
#   5. make frontend     (start Vite dev server in a second terminal)
#      Then open http://localhost:5173

COMPOSE      = docker compose -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_EXEC = $(COMPOSE) exec

.PHONY: setup dev down migrate frontend restart-worker purge \
        logs shell-api shell-db seed build install lock lint format test fresh prod

# ── First-time setup ──────────────────────────────────────────────────────────

setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
		echo "  -> Fill in GITHUB_TOKEN and GROQ_API_KEY then run: make dev"; \
	else \
		echo ".env already exists"; \
	fi
	cd frontend && npm install

# ── Backend (Docker Compose) ──────────────────────────────────────────────────

dev:
	$(COMPOSE) up

down:
	$(COMPOSE) down

# Wipe volumes and start completely fresh (re-runs migrations from zero)
fresh:
	$(COMPOSE) down -v
	$(COMPOSE) up

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	$(COMPOSE_EXEC) api alembic upgrade head

makemigration:
	$(COMPOSE_EXEC) api alembic revision --autogenerate -m "$(msg)"

# ── Frontend ──────────────────────────────────────────────────────────────────

# Run in a separate terminal after `make dev`
frontend:
	cd frontend && npm run dev

# ── Celery worker ─────────────────────────────────────────────────────────────

# Worker starts automatically with `make dev`.
# Use this to restart it after changing task code without restarting everything.
restart-worker:
	$(COMPOSE) restart worker

# Discard all pending Celery tasks from Redis without wiping the database.
# Run this before `make dev` if the worker picks up stale jobs from a previous session.
purge:
	$(COMPOSE_EXEC) worker celery -A app.workers.celery_app purge -f
	@echo "All pending tasks purged."

# ── Logs ─────────────────────────────────────────────────────────────────────

# Usage: make logs          (all services)
#        make logs service=worker
logs:
	$(COMPOSE) logs -f $(service)

# ── Shells ───────────────────────────────────────────────────────────────────

shell-api:
	$(COMPOSE_EXEC) api bash

shell-db:
	$(COMPOSE) exec postgres psql -U codesense -d codesense

# ── Data ─────────────────────────────────────────────────────────────────────

seed:
	$(COMPOSE_EXEC) api uv run python -m app.scripts.seed

# ── Build ────────────────────────────────────────────────────────────────────

build:
	$(COMPOSE) build --no-cache

# ── Python (run locally, outside Docker) ────────────────────────────────────

install:
	cd backend && uv sync

lock:
	cd backend && uv lock

lint:
	$(COMPOSE_EXEC) api uv run ruff check .

format:
	$(COMPOSE_EXEC) api uv run ruff format .

test:
	cd backend && uv run pytest tests/ -v

# ── Production ───────────────────────────────────────────────────────────────

prod:
	docker compose -f docker-compose.yml up
