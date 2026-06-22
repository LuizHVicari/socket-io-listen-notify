FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# dependencies first (cache layer) — without the project, without dev deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# source
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "app.api:socket_app", "-c", "gunicorn.config.py"]
