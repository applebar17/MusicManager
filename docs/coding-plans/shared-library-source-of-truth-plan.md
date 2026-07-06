# Shared Library Source Of Truth Plan

## Purpose

Introduce a shared, non-playlist-organized music library that becomes the durable
source of truth for all managed USB exports. SoundCloud songs should map to library
tracks, and export plans should copy from the library into one or more organized USB
environments.

This feature separates three concepts that are currently coupled:

- SoundCloud playlist membership: remote intent and ordering.
- Shared library: canonical audio files and reusable metadata.
- USB environment: plugged target device and app-managed export state.

## Locked Decisions

- Library layout is flat for now, so files remain easy to manage outside the app.
- Song/library matching identity is normalized title plus duration.
- Metadata conflicts use latest import wins.
- Creating or aligning a library from a USB never deletes from the library.
- Export planning should use library tracks as the preferred source for USB writes.
- A dedicated Library page is required.
- Existing USB workflows can remain while the library is introduced gradually.

## Feature Requirements

### Shared Library

- Add a globally configured library root path.
- Allow creating the library from an empty base folder.
- Allow initializing or aligning the library from the currently selected USB
  environment.
- Store canonical audio files in the flat library root.
- Import songs from USB into the library when no matching library track exists.
- Keep library-only songs even when they are absent from the current USB.
- Never delete library audio during alignment.

### Matching And Source Of Truth

- Add a library track model separate from USB `AudioFile` rows.
- Match SoundCloud songs to library tracks by normalized title plus duration.
- Use the library mapping as the primary link for export.
- Keep USB/download files as import candidates, not long-term export sources, once a
  library mapping exists.
- Preserve manual review for ambiguous normalized title/duration collisions.

### Metadata Preservation

- Import sidecar metadata from USB folders during alignment.
- Preserve `tracks.json`, `_Serato`, and unknown metadata files/folders.
- Compact discovered `tracks.json` files into one library-level metadata index.
- Attach metadata entries to matched library tracks when possible.
- Use latest import wins when the same metadata field conflicts.
- Keep enough source/provenance fields to troubleshoot where imported metadata came
  from.

### USB Export

- Export plans should prefer library files as source paths.
- Existing USB files can still be detected as already present.
- Export should keep organizing by playlist on the USB target.
- Export should eventually write or restore relevant metadata sidecars when the target
  format is understood.

### Frontend

- Add a dedicated Library page.
- Show library setup state, configured path, scan/import status, track count, and
  metadata inventory.
- Provide an action to align the library from the selected USB.
- Show SoundCloud-to-library mapping status.
- Show duplicate/ambiguous library import review states.

## Design Notes

- Treat the library as global application configuration, not per USB environment.
- Keep existing environments as USB targets.
- Keep filesystem-changing actions explicit and previewable where practical.
- Use current backend layering: domain entities, repository ports, use cases,
  persistence migrations, API routes, then frontend API wrappers and feature UI.
- Avoid deep parsing of vendor metadata in V1. Store raw metadata safely first, then
  add format-specific behavior later.

## Open Points

- Exact flat filename convention:
  - normalized title only,
  - artist plus title,
  - original filename with collision suffix.
- Duration tolerance for library matching:
  - reuse current strict/loose seconds tolerance,
  - or use a percentage tolerance like the deprecated-folder duplicate check.
- Whether artist participates in automatic library identity or only in ambiguity
  scoring.
- Whether latest metadata import wins globally or per metadata provider/source.
- How to represent metadata that belongs to a playlist folder rather than a single
  track.
- Whether the library path should be stored in a new app settings table or as a special
  environment type.
- Whether USB alignment should copy audio immediately or first create a preview plan.

## Multi-Wave Plan

### Wave 1: Library Configuration And Persistence

Goal: add a durable shared library concept without changing existing export behavior.

Locked Wave 1 decisions:

- The library is a singleton global source of truth with fixed id `default`.
- The frontend includes a minimal Library page for setup/status only.
- The configured root path must be an existing readable and writable folder.
- Wave 1 does not create folders, scan audio, copy USB files, import metadata, map
  SoundCloud songs, or change export planning.

Deliverables:

- Add a singleton `libraries` table.
- Store library root path and creation timestamp.
- Add `library_tracks` table with canonical path, title, artist, duration, file hash
  placeholder, and timestamps.
- Add repositories and domain entities for library settings and library tracks.
- Add API routes to get/update library configuration.
- Add a minimal frontend Library navigation page showing configured state, root path,
  and track count.

Tests:

- Library path can be saved and retrieved.
- Invalid paths are rejected.
- Library tracks persist and survive restart.

Exit criteria:

- Backend and frontend can display whether a shared library is configured.

### Wave 2: Library Scan And USB Alignment Import

Goal: populate the library from an existing USB while preserving existing files.

Locked Wave 2 decisions:

- Imported USB files keep the original filename, with numeric suffixes for flat-library
  filename collisions.
- Alignment writes immediately and returns a persisted summary; there is no preview/apply
  workflow in this wave.
- Matching uses normalized title plus exact rounded duration seconds.
- Library files missing from disk are marked missing, not deleted from the database.
- Alignment collision/review items are persisted for a later resolution UI.

Deliverables:

- Add library scanner for supported audio files in the flat library root.
- Add USB-to-library alignment use case.
- Match USB audio to existing library tracks by normalized title plus duration.
- Copy unmatched USB audio into the library using the chosen flat filename convention.
- Detect collisions and create review items instead of overwriting.
- Never delete library files during alignment.

Tests:

- Alignment copies USB-only songs into the library.
- Existing matching library tracks are reused.
- Library-only songs are preserved.
- Colliding normalized title/duration cases are marked for review.

Exit criteria:

- A current USB can seed a usable shared library.

### Wave 3: Metadata Import And Compaction

Goal: preserve USB-side metadata during alignment.

Locked Wave 3 decisions:

- Raw metadata assets live under the library root in
  `_music_manager/metadata-assets`.
- `tracks.json` is parsed only enough for raw-plus-index compaction; cue/grid
  interpretation is deferred.
- Latest import wins at provider plus entry-key level.
- The Library page shows counts and latest import summary only.
- Provider-specific metadata interpretation/export remains Wave 7.

Deliverables:

- Discover `tracks.json` files under the USB root.
- Compact imported `tracks.json` entries into one library metadata index.
- Import `_Serato` and unknown metadata folders/files as raw metadata assets.
- Store metadata source path, imported timestamp, provider/type, and associated library
  track when matchable.
- Apply latest import wins for direct metadata conflicts.

Tests:

- Multiple `tracks.json` files compact into one library index.
- Latest import updates conflicting metadata.
- Unknown metadata files are preserved rather than discarded.
- Metadata can be associated with a matched library track.

Exit criteria:

- Aligning from USB preserves audio and known sidecar metadata into the library.

### Wave 4: SoundCloud To Library Mapping

Goal: make the library the primary match target for remote songs.

Locked Wave 4 decisions:

- Library matching runs in parallel with existing USB/audio-file matching.
- Existing export behavior does not change until Wave 5.
- Automatic matching uses normalized title plus exact rounded duration seconds.
- Manual library mappings override automatic matches and survive reruns.
- Only active library tracks are eligible.

Deliverables:

- Add `song_library_links` as the song-to-library-track mapping table.
- Match SoundCloud songs to library tracks by normalized title plus duration.
- Preserve manual review for ambiguous matches.
- Update playlist detail/matching views to show library mapping status.
- Keep existing local audio matches as fallback when no library is configured.

Tests:

- Imported SoundCloud songs map to existing library tracks.
- Ambiguous library matches require review.
- Manual library mapping overrides automatic results.
- Existing non-library workflows still work without configured library.

Exit criteria:

- Remote playlist readiness can be determined from library coverage.

### Wave 5: Export From Library To USB

Goal: use library tracks as the source for organized USB exports.

Locked Wave 5 decisions:

- A configured library makes library mappings required for active exports.
- New copied USB files use the library track filename.
- Correctly placed existing USB copies are kept instead of recopied.
- When no library is configured, legacy audio-file export behavior remains unchanged.
- Apply allows active library tracks as approved copy sources.

Deliverables:

- Update export planning to prefer mapped library track paths.
- Keep existing USB copies as `keep_existing` when already correct.
- Continue stale duplicate/removal behavior for app-managed USB files.
- Keep plan editing and live apply progress behavior unchanged.
- Add clear skip reasons when a SoundCloud song has no library mapping.

Tests:

- Export plans copy from library paths.
- Existing USB files are kept when already in place.
- Missing library mappings become skips.
- Excluding/reordering export actions still validates correctly.

Exit criteria:

- A USB can be rebuilt from SoundCloud playlist order using library files as the source
  of truth.

### Wave 6: Library Inspection And Navigation

Goal: expand the existing Library page into the inspection workspace for current
library data.

Deliverables:

- Keep the existing Library setup, scan, align, and metadata import actions.
- Add read APIs for library tracks, metadata assets, and metadata index entries.
- Show Overview, Tracks, Metadata, and Issues sections in the Library page.
- Show searchable/filterable track inventory with active/missing and mapped/unmapped
  state.
- Show metadata asset and compacted index-entry inventories using the existing
  persisted metadata rows.
- Show issue rows from persisted alignment items and metadata asset errors.
- Keep the typed root path field; folder browsing is a progressive enhancement.
- Link from playlist and matching views to the Library page focused on a mapped
  library track.

Locked decisions:

- The Library page is expanded rather than recreated.
- Inventory is read-only in this wave.
- Metadata inventory shows assets, index entries, and issue rows, not resolved
  provider conflicts.
- Provider-specific cue/grid interpretation remains Wave 7.
- Cross-view links are navigational only and do not change matching, playlist, or
  export state.

Tests:

- Library inventory endpoints reject an unconfigured library and return configured
  track/metadata rows.
- Library setup and refresh still render and call the correct APIs.
- Track search and active/missing plus mapped/unmapped filters work.
- Metadata inventory displays imported metadata assets and index entries.
- Playlist and matching rows render Library links only when a library track id is
  available.

Exit criteria:

- The user can inspect current shared library contents and navigate to mapped
  library tracks from playlist and matching workflows.

### Wave 7: Metadata Export And Provider-Specific Enhancements

Goal: use the library master `tracks.json` index to regenerate playlist-local
metadata files during USB export.

Deliverables:

- Treat `{library_root}/_music_manager/metadata-index/tracks.json` as the master
  `tracks.json` source of truth.
- Rewrite the master index after each USB metadata import from persisted latest-win
  index entries.
- Add explicit `write_tracks_json` export-plan actions.
- Generate one `tracks.json` per exported playlist folder, ordered by playlist order.
- Derive playlist metadata entries from active song-to-library mappings and the master
  index.
- Rewrite path-like fields (`filename`, `path`, `file`, `location`, `url`) to the
  exported playlist filename.
- Block unmanaged existing playlist `tracks.json` files; overwrite only app-owned
  metadata targets.
- Track successful metadata writes in the export manifest for future stale cleanup.

Locked Wave 7 decisions:

- Scope is `tracks.json` only.
- `_Serato`, unknown raw metadata restore, and cue/grid interpretation are deferred.
- Exported playlist `tracks.json` files are derived artifacts and can be regenerated.
- Latest import wins remains the conflict policy.
- The master index remains app-managed under `_music_manager`, not in the visible
  flat audio root.

Tests:

- Metadata import updates the persisted master index and master file.
- Export preview creates playlist-folder `tracks.json` actions from master entries.
- Generated metadata follows playlist order and rewrites path-like fields.
- Tracks without master metadata do not block audio export.
- Existing unmanaged playlist `tracks.json` marks the plan invalid.
- Apply writes valid JSON with per-item live progress.
- Frontend renders `write_tracks_json` actions through the existing export plan UI.

Exit criteria:

- USB exports carry regenerated playlist-local `tracks.json` metadata derived from the
  shared library master index.
