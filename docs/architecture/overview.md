# Architecture Overview

## Application Shape

Music Manager is a desktop app built with Tauri, a TypeScript frontend, and a Python
backend. The app is local-first and centered on filesystem, USB, playback, matching,
and export workflows.

## Proposed Layers

### Ingestion Layer

Responsible for importing remote playlist knowledge.

Initial provider:

- SoundCloud public playlist URLs;
- SoundCloud API or SDK when credentials are available.

### Normalization Layer

Converts provider-specific playlist and track data into internal entities:

- Source;
- RemotePlaylist;
- SongMaster candidates;
- Playlist;
- PlaylistItem;
- sync snapshots.

### Library Layer

Owns canonical songs, playlists, local overrides, playlist membership, and sync state.

This layer should know that one song may belong to many playlists.

### Environment Scan Layer

Scans folders and USB drives linked to a named environment/workspace, producing
AudioFile records and embedded metadata when available.

### Matching Layer

Connects SongMaster records to AudioFile records through automatic and manual matching.

This layer owns match confidence, ambiguity, missing-audio status, and manual mappings.

### Playback Layer

Plays accepted local audio files for verification.

### Analysis Layer

Stores or computes BPM, key, cue points, and other DJ preparation metadata.

This can remain thin in the MVP.

### Export Layer

Generates planned USB changes from playlists, accepted mappings, and an export profile.

This layer should support multiple strategies:

- physical duplication for the v1 generic USB folder mirror;
- shared master folder plus references where compatible;
- ecosystem-specific databases later.

### Dashboard Layer

Presents the user workflow:

- import playlists;
- scan environment;
- review missing audio;
- resolve ambiguous matches;
- map unmatched files;
- preview export;
- apply export.

## Data Flow

```text
SoundCloud playlist/API
  -> ingestion
  -> normalization
  -> canonical library
  -> matching with local environment scan
  -> dashboard review
  -> export plan
  -> user confirmation
  -> USB apply
```

## Storage Needs

The application will need persistent local storage for:

- imported sources and playlists;
- remote sync snapshots;
- canonical songs;
- local overrides;
- environments/workspaces;
- scanned audio file inventory;
- match links;
- export targets and export history;
- DJ metadata.

SQLite is the current default storage choice unless implementation discovery finds a
better local persistence fit.

## Safety Boundary

Sync, scan, and preview operations should be read-heavy and safe.

Export apply is the main write operation and should be isolated behind a clear preview
step, explicit confirmation, and conservative file handling.
