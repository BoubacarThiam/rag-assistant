# Hugging Face Spaces image: one container serving the API (under /api) and the React build,
# on port 7860. Built from the folder assembled by deploy.py (backend/ and frontend/ inside).

FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/

# Spaces run the container as the user with id 1000.
RUN useradd --create-home --uid 1000 user

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/hf-cache \
    ENVIRONMENT=prod \
    API_PREFIX=/api \
    STATIC_DIR=/app/static

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Download the embedding model during the build (~1 GB): the first PDF import is then
# immediate, and the running app never needs to reach the model hub.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('intfloat/multilingual-e5-base', device='cpu')" \
    && chmod -R a+rX /opt/hf-cache
ENV HF_HUB_OFFLINE=1

COPY backend/ ./
COPY --from=frontend /frontend/dist ./static

USER user
EXPOSE 7860
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 7860 --proxy-headers --forwarded-allow-ips='*'"]
