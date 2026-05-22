# Technology Stack

## Selected Direction

Music Manager should be built as a desktop app using:

- Tauri for the desktop shell;
- TypeScript for the frontend;
- Python for the backend and local music-management logic;
- SQLite for local persistence unless a later implementation discovery shows a better
  local database fit.

## Responsibilities

### TypeScript frontend

The frontend should own:

- dashboard navigation;
- playlist and library views;
- missing-audio and ambiguous-match review;
- manual mapping workflows;
- local playback controls;
- export plan preview and apply confirmation;
- environment/workspace selection.

### Python backend

The backend should own:

- SoundCloud ingestion adapters;
- local database access;
- filesystem and USB scanning;
- audio metadata reading;
- conservative matching;
- export plan generation;
- export apply operations;
- future audio analysis integrations.

### Tauri shell

The shell should provide:

- desktop packaging;
- local filesystem permissions;
- safe communication between frontend and backend;
- access to native dialogs where useful, such as selecting a folder or USB drive.

## Implementation Note

The early implementation can keep a clean local API boundary between the TypeScript UI
and Python backend. That keeps the product easy to iterate while still matching the
intended desktop architecture.

