# syntax=docker/dockerfile:1

# Etapa 1: monta o front (React + Vite). VITE_BACKEND_URL vazio = o front
# chama a API na mesma origem, porque a propria API serve estes arquivos.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_BACKEND_URL=""
RUN npm run build

# Etapa 2: instala as dependencias Python num venv, sem o grupo
# dev/analysis. numpy/scipy/pandas ficam fora: a API so le o JSON que
# compute_stats.py calculou (spec 9.6).
FROM python:3.12-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
# cache do uv num mount de build: nao entra na imagem
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Alvo de teste: mesma base + dependencias dev (pytest, httpx) e os testes.
# Nao e o padrao do `docker build` (o ultimo estagio, runtime, e).
# docker compose --profile test run --rm test
FROM deps AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/seed ./seed
COPY backend/tests ./tests
COPY backend/tests_integration ./tests_integration
CMD ["pytest", "-v", "tests_integration"]

# Etapa 3: imagem final, so o venv + codigo + front montado (sem uv, sem Node)
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/seed ./seed
COPY --from=frontend /frontend/dist ./static

RUN useradd --create-home --uid 10001 apitacerto && chown -R apitacerto /app
USER apitacerto

ENV STATIC_DIR=/app/static
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
