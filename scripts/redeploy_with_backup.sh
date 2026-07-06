#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$ROOT_DIR/local/music-manager.sqlite3"
BACKUP_DIR="$ROOT_DIR/local/backups"
COMPOSE_FILE="$ROOT_DIR/compose.yml"

usage() {
  cat <<'EOF'
Usage: bash scripts/redeploy_with_backup.sh [options]

Backs up the local SQLite database, rebuilds/recreates Docker containers, and
prints validation commands for USB/library path visibility.

Options:
  --no-build      Recreate containers without rebuilding images.
  --logs          Follow backend logs after containers start.
  --skip-backup   Do not create a database backup.
  -h, --help      Show this help.

Examples:
  bash scripts/redeploy_with_backup.sh
  bash scripts/redeploy_with_backup.sh --logs
  bash scripts/redeploy_with_backup.sh --no-build
EOF
}

NO_BUILD=0
FOLLOW_LOGS=0
SKIP_BACKUP=0

for arg in "$@"; do
  case "$arg" in
    --no-build)
      NO_BUILD=1
      ;;
    --logs)
      FOLLOW_LOGS=1
      ;;
    --skip-backup)
      SKIP_BACKUP=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      usage
      exit 2
      ;;
  esac
done

cd "$ROOT_DIR"

echo "Music Manager redeploy"
echo "Project: $ROOT_DIR"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "compose.yml not found at $COMPOSE_FILE" >&2
  exit 1
fi

if [[ -z "${HOME:-}" ]]; then
  echo "HOME is not set. Set HOME before running so compose.yml path mounts resolve." >&2
  echo "PowerShell example: \$env:HOME = \$env:USERPROFILE" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI is not installed or not on PATH." >&2
  exit 1
fi

if ! docker version >/dev/null 2>&1; then
  echo "Docker is not reachable. Start Docker Desktop, then rerun this script." >&2
  exit 1
fi

if [[ "$SKIP_BACKUP" -eq 0 ]]; then
  if [[ -f "$DB_PATH" ]]; then
    mkdir -p "$BACKUP_DIR"
    timestamp="$(date +%Y%m%d-%H%M%S)"
    backup_path="$BACKUP_DIR/music-manager-$timestamp.sqlite3"
    cp "$DB_PATH" "$backup_path"
    echo "Database backup created:"
    echo "  $backup_path"
  else
    echo "No database found at $DB_PATH; skipping backup."
  fi
else
  echo "Skipping database backup by request."
fi

echo
echo "Stopping current containers..."
docker compose down

echo
if [[ "$NO_BUILD" -eq 1 ]]; then
  echo "Recreating containers without rebuild..."
  docker compose up -d --force-recreate
else
  echo "Building and recreating containers..."
  docker compose up -d --build --force-recreate
fi

echo
echo "Container status:"
docker compose ps

echo
echo "Backend health check:"
if command -v curl >/dev/null 2>&1; then
  if curl -fsS http://localhost:8000/health >/dev/null; then
    echo "  backend health: ok"
  else
    echo "  backend health: not ready yet; check logs with: docker compose logs -f backend"
  fi
else
  echo "  curl not found; open http://localhost:8000/health in a browser."
fi

cat <<EOF

Next checks:
  Frontend: http://localhost:1420
  Backend:  http://localhost:8000/health

USB visibility:
  docker compose exec backend sh -lc 'ls -la /Volumes'
  docker compose exec backend sh -lc 'ls -la /Volumes/YOUR_USB_NAME'

Library writability:
  docker compose exec backend sh -lc 'touch "$HOME/Desktop/SomeMusic/.write-test" && rm "$HOME/Desktop/SomeMusic/.write-test"'

Rollback, if needed:
  docker compose down
  cp local/backups/<backup-file>.sqlite3 local/music-manager.sqlite3
  docker compose up -d
EOF

if [[ "$FOLLOW_LOGS" -eq 1 ]]; then
  echo
  echo "Following backend logs..."
  docker compose logs -f backend
fi
