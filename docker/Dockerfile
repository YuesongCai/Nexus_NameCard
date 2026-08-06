# syntax=docker/dockerfile:1

# ---- stage 1: build the SPA -------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /build

COPY web/package.json web/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY web/ ./
RUN npm run build


# ---- stage 2: runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY api/pyproject.toml ./api/
COPY api/src ./api/src
RUN pip install --no-cache-dir ./api

COPY api/kb ./api/kb
COPY api/data ./api/data
COPY api/scripts ./api/scripts
COPY --from=web /build/dist ./web/dist

# Drop root before serving.
RUN useradd --create-home --uid 10001 nexus && chown -R nexus:nexus /app
USER nexus

ENV NEXUS_CARD_ENV=prod \
    NEXUS_CARD_KB_DIR=/app/api/kb \
    NEXUS_CARD_CARDS_DIR=/app/api/data/cards \
    NEXUS_CARD_INDEX_PATH=/app/api/data/kb_index.json \
    NEXUS_CARD_WEB_DIST_DIR=/app/web/dist

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=4s --start-period=15s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/healthz', timeout=3).status==200 else 1)"

CMD ["uvicorn", "nexus_card.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
