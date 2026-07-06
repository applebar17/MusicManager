#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI is not installed or not on PATH." >&2
  exit 1
fi

if ! docker compose ps backend >/dev/null 2>&1; then
  echo "Backend container is not available. Start it first with: docker compose up -d backend" >&2
  exit 1
fi

docker compose exec backend env PYTHONPATH=backend uv run python \
  -m music_manager_backend.tools.port_manual_audio_links_to_library "$@"
