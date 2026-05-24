FROM python:3.12-slim AS backend-deps

ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --all-groups

COPY alembic.ini ./
COPY backend ./backend

RUN uv run alembic upgrade head
RUN uv run ruff check backend
RUN uv run mypy backend
RUN uv run pytest

FROM node:20-bookworm AS frontend-checks

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY apps/desktop/package.json ./apps/desktop/package.json
RUN npm ci

COPY apps ./apps

RUN npm --workspace apps/desktop exec tsc -- --noEmit
RUN npm --workspace apps/desktop run test -- --run
RUN npm run desktop:build

FROM scratch AS ci

COPY --from=backend-deps /workspace/pyproject.toml /backend-ok
COPY --from=frontend-checks /workspace/apps/desktop/package.json /frontend-ok
