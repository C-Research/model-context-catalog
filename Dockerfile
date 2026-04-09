FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# Install the project itself
COPY mcc/ ./mcc/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

EXPOSE 8000

# Cache dir for fastembed model downloads
ENV HF_HOME=/cache/huggingface

CMD ["uv", "run", "--no-dev", "mcc", "mcp", "serve"]
