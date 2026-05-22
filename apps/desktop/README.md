# Desktop App

Tauri desktop shell with a TypeScript frontend.

## Frontend Folders

- `src/app/` - app shell and top-level composition.
- `src/features/environments/` - workspace and USB/folder context.
- `src/features/playlists/` - imported playlists and playlist readiness.
- `src/features/matching/` - missing audio, candidates, and manual mapping.
- `src/features/playback/` - local playback review controls.
- `src/features/export/` - export plans and apply workflow.
- `src/shared/` - reusable API clients and small UI primitives.

The UI should stay feature-oriented. Avoid large all-in-one screens as the product grows.

