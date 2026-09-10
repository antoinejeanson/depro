# depro — single image: built frontend + FastAPI backend.
# Build from the repo root:  docker build -t depro .

# ---- Stage 1: frontend -------------------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend + static assets ----------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-trixie
WORKDIR /srv/backend
# Install dependencies first (cached layer), then the app code.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev
COPY --from=frontend /build/dist /srv/web
RUN useradd -m appuser && mkdir -p /data && chown appuser:appuser /data
ENV DEPRO_DATA_DIR=/data \
    DEPRO_WEB_DIST=/srv/web
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD .venv/bin/python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
