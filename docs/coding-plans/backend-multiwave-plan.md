# Backend Multiwave Plan

## Purpose

This plan implements the backend stage first. The backend should become a reliable
local-first engine for environments, playlist ingestion, library storage, local audio
scanning, conservative matching, playback support, and USB export planning.

The frontend can stay thin while these backend capabilities mature.

## Backend Principles

- Keep the existing layer boundaries: `domain`, `application`, `ports`,
  `infrastructure`, `api`, and `shared`.
- Keep files small and topic-focused.
- Prefer explicit use cases over large manager classes.
- Domain code should not import infrastructure code.
- Every wave should include tests for the behavior it introduces.
- Export apply must stay separate from export planning.
- Filesystem writes should be conservative, previewable, and limited to app-managed
  areas.

## Wave 0: Backend Foundation

Goal: make the scaffold runnable and establish project conventions.

Deliverables:

- Confirm Python packaging/import paths.
- Add backend dependency lock strategy.
- Add dev commands for tests, linting, and local API startup.
- Add basic app settings with environment-specific paths.
- Add structured error types for domain/application failures.
- Add test fixtures for temporary music environments.

Suggested modules:

- `shared/settings.py`
- `shared/errors.py`
- `shared/time.py`
- `tests/fixtures/`

Tests:

- Backend imports cleanly.
- Health endpoint returns `ok`.
- Test fixtures can create temporary folders and sample files.

Exit criteria:

- A developer can run backend tests locally.
- The FastAPI app can start with no real SoundCloud or USB dependency.

## Wave 1: Local Persistence and Schema

Goal: replace in-memory placeholders with SQLite-backed repositories.

Deliverables:

- Define initial SQLite schema.
- Add migrations or schema bootstrap.
- Implement repositories for environments, playlists, songs, audio files, match links,
  sync snapshots, and export plans.
- Keep repository interfaces small and use-case oriented.
- Add serialization rules for paths, timestamps, and enum values.

Suggested modules:

- `infrastructure/persistence/schema.py`
- `infrastructure/persistence/migrations/`
- `infrastructure/persistence/sqlite_connection.py`
- `infrastructure/persistence/environment_repository.py`
- `infrastructure/persistence/playlist_repository.py`
- `infrastructure/persistence/song_repository.py`
- `infrastructure/persistence/audio_file_repository.py`
- `infrastructure/persistence/match_repository.py`
- `infrastructure/persistence/export_plan_repository.py`

Tests:

- Schema initializes on an empty database.
- Repositories can save and retrieve each core entity.
- Repositories preserve local overrides and manual mappings.
- Repeated schema initialization is idempotent.

Exit criteria:

- In-memory repositories are no longer used by normal API routes.
- Core data survives process restart.

## Wave 2: Environment Management and Folder Scanning

Goal: support multiple environments and scan local audio files.

Deliverables:

- Create, list, update, and archive environments.
- Link each environment to a root folder or USB path.
- Validate root path existence and permissions.
- Scan supported audio files recursively.
- Persist scan results.
- Detect added, removed, moved, and changed files across scans.
- Track unmanaged local files.

Suggested modules:

- `application/use_cases/create_environment.py`
- `application/use_cases/update_environment.py`
- `application/use_cases/scan_environment.py`
- `application/use_cases/list_unmanaged_files.py`
- `infrastructure/filesystem/local_audio_scanner.py`
- `infrastructure/filesystem/path_safety.py`

Tests:

- Environment CRUD works through use cases and API routes.
- Scanner finds supported files and ignores unsupported files.
- Scanner handles nested folders.
- Rescan detects missing or changed files.
- Path validation rejects unsafe or nonexistent roots.

Exit criteria:

- Backend can create an environment, scan a folder, persist audio files, and list scan
  results through the API.

## Wave 3: Audio Metadata Read Layer

Goal: enrich local audio files with embedded metadata where available.

Deliverables:

- Choose and integrate a Python audio metadata library.
- Read common tags: title, artist, album, duration, BPM, key, comments when available.
- Normalize absent or malformed tags safely.
- Keep metadata reading separate from filesystem scanning.
- Store raw readable metadata where useful for debugging.

Suggested modules:

- `infrastructure/audio/metadata_reader.py`
- `domain/entities/audio_metadata.py`
- `application/use_cases/read_audio_metadata.py`

Tests:

- Metadata reader handles sample MP3/WAV/AIFF/FLAC/M4A fixtures where practical.
- Missing tags do not fail scans.
- Corrupt or unreadable files are reported as warnings, not fatal scan failures.

Exit criteria:

- Scanned audio files can expose useful metadata to matching without blocking on every
  file being perfectly tagged.

## Wave 4: SoundCloud Public Playlist Discovery

Goal: support no-key public playlist import discovery before deciding how much can be
reliably automated.

Important note:

We likely need one or more saved HTML references from real public SoundCloud playlist
pages. Those references should be kept as fixtures so parser behavior can be tested
without network access or API keys.

Deliverables:

- Define `SoundCloudPlaylistImporter` behavior for public playlist URLs.
- Add fixture location for captured HTML references.
- Parse public playlist metadata from saved HTML if feasible.
- Extract playlist title, track order, track title, artist/uploader, duration, and
  public track URLs when present.
- Record parser limitations clearly.
- Add a fallback path for API-based ingestion if public HTML is insufficient or too
  unstable.

Suggested modules:

- `infrastructure/soundcloud/public_playlist_importer.py`
- `infrastructure/soundcloud/public_html_parser.py`
- `infrastructure/soundcloud/soundcloud_models.py`
- `tests/fixtures/soundcloud_html/`

Tests:

- Parser extracts playlist metadata from saved HTML fixtures.
- Parser reports missing fields without crashing.
- Importer maps parsed data into `RemotePlaylist`, `Playlist`, `SongMaster`, and
  `PlaylistItem` records.

Exit criteria:

- We know whether public playlist import is viable for v1.
- If viable, import works from saved HTML fixtures.
- If not viable, the API-auth path becomes the required ingestion path.

## Wave 5: SoundCloud Ingestion Persistence and Sync

Goal: turn imported SoundCloud playlist data into durable local library state.

Deliverables:

- Import public or API playlist data into the canonical library.
- Persist remote playlist snapshots.
- Create or update playlists and playlist items.
- Create conservative `SongMaster` records.
- Preserve local overrides across sync.
- Detect additions, removals, reorders, playlist renames, and metadata changes.
- Mark inactive playlist membership instead of deleting history.

Suggested modules:

- `application/use_cases/import_playlist.py`
- `application/use_cases/sync_playlist.py`
- `domain/services/song_identity.py`
- `domain/services/sync_diff.py`
- `infrastructure/soundcloud/api_playlist_importer.py`

Tests:

- First import creates source, remote playlist, local playlist, songs, and memberships.
- Reimport without changes is idempotent.
- Added and removed remote tracks are detected.
- Local playlist and song overrides survive sync.
- Different mixes/versions are not merged by title alone.

Exit criteria:

- Backend can import/sync a SoundCloud playlist into durable local state and report the
  detected sync changes.

## Wave 6: Conservative Matching Engine

Goal: match canonical songs to local audio files without dangerous overconfidence.

Deliverables:

- Implement normalized title and artist comparison.
- Add duration tolerance as a configurable signal.
- Add filename heuristic as a lower-confidence signal.
- Produce match states: matched, missing audio, ambiguous, manually mapped.
- Persist automatic and manual match links.
- Preserve manual mappings across rescans.
- Provide manual mapping APIs.

Suggested modules:

- `domain/services/match_scoring.py`
- `domain/services/title_normalizer.py`
- `application/use_cases/match_songs.py`
- `application/use_cases/create_manual_mapping.py`
- `application/use_cases/list_match_review_queue.py`

Tests:

- Exact title/artist matches are accepted.
- Different mixes are not merged automatically when metadata suggests version mismatch.
- Multiple candidates become ambiguous.
- No candidates become missing audio.
- Manual mappings override future automatic guesses unless the file disappears.

Exit criteria:

- Backend can produce a reviewable matching state for all songs in an environment.

## Wave 7: Playback Support API

Goal: let the desktop app play local files safely during match review.

Deliverables:

- Add API route for requesting playback access to a matched or candidate local file.
- Prevent arbitrary file reads outside linked environment roots.
- Support range requests if needed by the frontend audio element.
- Return clear unavailable states for missing, deleted, or ambiguous files.

Suggested modules:

- `api/routers/playback.py`
- `application/use_cases/get_playback_file.py`
- `infrastructure/filesystem/path_safety.py`

Tests:

- Valid environment files can be served or resolved for playback.
- Files outside the environment root are rejected.
- Missing files return a clear error.

Exit criteria:

- The frontend can play a local candidate file for manual matching review.

## Wave 8: Export Planning

Goal: generate a complete USB folder mirror plan without applying changes yet.

Deliverables:

- Generate playlist-folder export plans for selected playlists.
- Include folder creation, file copies, stale-copy removal, deprecated preservation,
  skipped missing tracks, and ambiguous tracks.
- Sanitize folder and filenames for common USB filesystems.
- Detect filename collisions.
- Persist export plans and summary counts.
- Keep export planning read-only.

Suggested modules:

- `domain/services/filename_sanitizer.py`
- `domain/services/export_layout.py`
- `application/use_cases/plan_export.py`
- `application/use_cases/list_export_plan.py`

Tests:

- Plan creates one folder per playlist.
- Shared songs appear in multiple playlist folders in physical-duplication mode.
- Removed songs are planned for stale-copy removal from app-managed playlist folders.
- Songs absent from all active playlists are planned for deprecated-folder preservation.
- Missing and ambiguous songs are skipped with reasons.
- Planning does not write to disk.

Exit criteria:

- Backend can explain every planned USB change before any filesystem write happens.

## Wave 9: Export Apply

Goal: safely apply a confirmed export plan.

Deliverables:

- Apply only persisted, user-confirmed export plans.
- Create folders.
- Copy files.
- Remove stale app-managed playlist-folder copies.
- Preserve deprecated files.
- Record apply results and failures.
- Keep source audio safe.
- Make repeated apply reasonably idempotent.

Suggested modules:

- `application/use_cases/apply_export_plan.py`
- `infrastructure/filesystem/export_file_writer.py`
- `infrastructure/filesystem/app_managed_paths.py`

Tests:

- Apply creates expected folders and files.
- Apply does not delete source audio.
- Apply refuses to touch paths outside app-managed export areas.
- Partial failures are recorded.
- Reapplying the same plan does not corrupt output.

Exit criteria:

- Backend can perform a v1 generic USB folder mirror export safely after confirmation.

## Wave 10: Backend Readiness for Desktop Integration

Goal: stabilize the backend API for the first desktop vertical slice.

Deliverables:

- Review API route naming and response shapes.
- Add DTOs for frontend-friendly environment, playlist, matching, playback, and export
  views.
- Add pagination or filtering where needed for large libraries.
- Add background task status for long scans/imports/exports.
- Add API error response conventions.
- Add smoke tests for the main workflow.

Suggested modules:

- `api/routers/environments.py`
- `api/routers/playlists.py`
- `api/routers/scans.py`
- `api/routers/matching.py`
- `api/routers/export.py`
- `application/dtos/`

Tests:

- End-to-end backend workflow: create environment, scan files, import fixture playlist,
  match songs, produce export plan.
- Long-running operations expose status.
- API errors are consistent and frontend-readable.

Exit criteria:

- The desktop app can build its first useful UI on stable backend endpoints.

## Suggested First Vertical Slice

After Wave 0 and Wave 1, the first user-visible backend slice should be:

1. Create an environment.
2. Link it to a local folder.
3. Scan audio files.
4. Persist scan results.
5. List scanned files through the API.

This slice avoids SoundCloud uncertainty while proving the local-first foundation.

## Known Research Tasks

- Capture one or more public SoundCloud playlist HTML files for parser fixtures.
- Confirm what data public playlist pages expose without credentials.
- Decide whether public HTML import is acceptable for v1 or whether API credentials are
  mandatory.
- Choose the audio metadata library.
- Confirm v1 supported audio formats.
- Decide deprecated folder default name and path convention.

