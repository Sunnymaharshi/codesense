# ── codesense Makefile ──
# Usage: make <target>

.PHONY: dev prod down migrate makemigration test worker logs shell-api shell-db seed build install lock

# Start all services with hot reload
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Start without dev overrides
prod:
	docker compose -f docker-compose.yml up

# Stop and remove containers
down:
	docker compose down

# Run alembic migrations
migrate:
	docker compose exec api uv run alembic upgrade head

# Create a new migration (usage: make makemigration msg="add snapshot table")
makemigration:
	docker compose exec api uv run alembic revision --autogenerate -m "$(msg)"

# Run all tests
test:
	docker compose exec api uv run pytest tests/ -v
	cd frontend && npm run test

# Tail logs for a service (usage: make logs service=api)
logs:
	docker compose logs -f $(service)

# Shell into the api container
shell-api:
	docker compose exec api bash

# Connect to Postgres with psql
shell-db:
	docker compose exec postgres psql -U codesense -d codesense

# Seed sample GitHub profiles
seed:
	docker compose exec api uv run python -m app.scripts.seed

# Build fresh (after pyproject.toml changes)
build:
	docker compose build --no-cache

# Install/sync deps locally (outside Docker, for IDE support)
install:
	cd backend && uv sync

# Update lockfile after changing pyproject.toml
lock:
	cd backend && uv lock

# Lint
lint:
	docker compose exec api uv run ruff check .

# Format
format:
	docker compose exec api uv run ruff format .