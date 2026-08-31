FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"

# Dependencies first so an app-code change doesn't invalidate this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# deploy/docker-compose.yml overrides this per service (alembic+uvicorn for
# the api, arq for the worker) — this is just a sane default for running
# the image standalone.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
