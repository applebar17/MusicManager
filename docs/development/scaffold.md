# Scaffold Notes

The project is organized around product layers rather than technical convenience files.

## Root

- `docs/` captures product requirements and decisions.
- `backend/` contains the Python backend.
- `apps/desktop/` contains the Tauri and TypeScript desktop app.

## Backend Pattern

The backend follows a ports-and-adapters shape:

```text
api -> application -> domain
application -> ports
infrastructure -> ports
```

Domain code should not import infrastructure code. Use cases can depend on ports, and
infrastructure adapters implement those ports.

## Frontend Pattern

The frontend is feature-first:

```text
app
features/environments
features/playlists
features/matching
features/playback
features/export
shared
```

Each feature should own its types, components, hooks, and API calls when they become
specific to that feature.

## Current Status

This is a scaffold only. The next implementation step should be a thin vertical slice:

1. create an environment;
2. scan a folder for audio files;
3. show scanned files in the desktop UI.

