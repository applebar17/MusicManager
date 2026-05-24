FROM python:3.12-slim AS backend

ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --all-groups

COPY alembic.ini ./
COPY backend ./backend

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "music_manager_backend.api.app:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
