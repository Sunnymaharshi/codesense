FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH"

# Install all dependencies (including dev) into /venv
# --no-install-project: project source isn't available at build time (mounted as volume)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --dev

# Verify binaries are present at build time — fails fast if lockfile is broken
RUN /venv/bin/uvicorn --version && /venv/bin/celery --version

COPY . .

EXPOSE 8000

CMD ["/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]