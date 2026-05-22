# Backend

Python backend for Music Manager.

## Layers

- `domain/` - core entities and pure domain services.
- `application/` - use cases that coordinate domain logic and ports.
- `ports/` - interfaces for persistence, filesystem, SoundCloud, matching, and export.
- `infrastructure/` - adapters for local files, audio metadata, persistence, and providers.
- `api/` - FastAPI routers exposed to the desktop frontend.
- `shared/` - small cross-cutting utilities.

Keep modules small and topic-focused. Prefer adding a new file for a new workflow or
adapter instead of growing a large service file.

