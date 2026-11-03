# ビルドコンテキストはリポジトリルートです:
#   docker build -f apps/mcp-server/Dockerfile -t mcp-server .
FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 依存関係のみ先にインストール(キャッシュ効率化)
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/README.md apps/api/
COPY apps/mcp-server/pyproject.toml apps/mcp-server/README.md apps/mcp-server/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package mcp-server --no-install-workspace

# アプリ本体
COPY apps/mcp-server/src apps/mcp-server/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package mcp-server --no-editable

ENV PATH="/app/.venv/bin:$PATH"

RUN useradd --system --no-create-home app
USER app

EXPOSE 8001
CMD ["python", "-m", "mcp_server.main"]
