# Non-Functional Requirements

## Data Safety

- NFR-001: The system should be safe by default and avoid irreversible file operations.
- NFR-002: The system shall not permanently delete audio files during sync.
- NFR-003: The system shall provide a preview before reorganizing or exporting files.
- NFR-004: The system should support rollback or recovery for export operations where
  practical.
- NFR-005: Export cleanup shall be limited to app-managed export folders unless the
  user explicitly authorizes broader file operations.

## Reliability

- NFR-006: Repeated syncs should be idempotent when remote data has not changed.
- NFR-007: Repeated exports with the same inputs should produce the same planned
  output.
- NFR-008: Manual mappings and local overrides should survive remote refreshes and
  local rescans.
- NFR-009: Export plans should be reviewable before apply and should report counts for
  copied, moved, removed-from-playlist-folder, deprecated, skipped, and failed files.

## Auditability

- NFR-010: The system should keep enough sync history to explain why a song is present,
  missing, removed, deprecated, or unmanaged.
- NFR-011: The system should record whether a mapping was automatic or manual.
- NFR-012: The system should show the source playlist or source URL behind imported
  data.

## Extensibility

- NFR-013: The ingestion layer should allow additional providers beyond SoundCloud.
- NFR-014: The export layer should allow multiple target profiles.
- NFR-015: The matching layer should allow future matching signals such as audio
  fingerprints.
- NFR-016: DJ metadata storage should not assume a single consumer such as Serato,
  Rekordbox, or Pioneer hardware.

## Compatibility

- NFR-017: Exported files and folders should use names compatible with common USB
  filesystems.
- NFR-018: The system should account for filename collisions, invalid characters, and
  path-length limits.
- NFR-019: The export model should work even when the target DJ system does not support
  references to a shared master file.

## Privacy and Security

- NFR-020: SoundCloud credentials and API tokens shall be stored securely.
- NFR-021: The system shall not upload local audio files unless a future feature
  explicitly requires it and the user approves it.
- NFR-022: Public playlist URL import should not require credentials.

## Performance

- NFR-023: Local rescans should handle large music folders without blocking the whole
  application indefinitely.
- NFR-024: Matching should be incremental where possible after the first full scan.
- NFR-025: The dashboard should remain responsive while scanning, syncing, and export
  previews are running.

## Platform

- NFR-026: The application should be delivered as a desktop app using Tauri,
  TypeScript, and Python.
- NFR-027: The Python backend should own filesystem scanning, matching, metadata
  handling, export planning, and local persistence.
- NFR-028: The TypeScript frontend should own the dashboard, review workflows,
  playback controls, and user interaction.
