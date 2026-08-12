FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# Install the project itself
COPY mcc/ ./mcc/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

EXPOSE 8000

# Cache dir for fastembed model downloads
ENV FASTEMBED_CACHE_PATH=/cache/fastembed

# Override at build time with --build-arg MCC_EMBEDDING_MODEL=... / MCC_EMBEDDING_DIMS=...
# to bake in a different model (see mcc/settings.yaml for the production pairing).
# Both are promoted to ENV so the running container uses the same model/dims it downloaded.
ARG MCC_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
ARG MCC_EMBEDDING_DIMS=384
ENV MCC_EMBEDDING_MODEL=${MCC_EMBEDDING_MODEL}
ENV MCC_EMBEDDING_DIMS=${MCC_EMBEDDING_DIMS}
RUN --mount=type=cache,target=/root/.cache/uv .venv/bin/mcc download

ENTRYPOINT [".venv/bin/mcc"]
CMD ["mcp", "serve"]
