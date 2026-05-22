# Functional Requirements

These are draft functional requirements derived from the initial discussion.

## Playlist Ingestion

- FR-001: The system shall import SoundCloud playlist data from public playlist URLs.
- FR-002: The system should support SoundCloud API authentication when user credentials
  are provided, using a SoundCloud SDK or generated API client based on the
  SoundCloud Swagger/OpenAPI description when practical.
- FR-003: The system shall store the remote playlist identifier or source URL.
- FR-004: The system shall store remote playlist name, track ordering, and available
  track metadata.
- FR-005: The system shall support refreshing previously imported playlists.

## Canonical Library

- FR-006: The system shall create a canonical song library from imported playlist
  tracks.
- FR-007: The system shall represent the same song only once in the canonical library
  when it can be confidently identified as the same mix/version.
- FR-008: The system shall represent playlist membership as references from playlists
  to canonical songs.
- FR-009: The system shall track which playlists contain each canonical song.
- FR-010: The system shall preserve historical knowledge of songs that are removed from
  a remote playlist instead of immediately deleting them.
- FR-011: The system shall treat different mixes, edits, remixes, bootlegs, or
  versions as separate canonical songs unless a user manually confirms they should map
  to the same local audio file.

## Local Overrides

- FR-012: The system shall allow local playlist display names to differ from remote
  playlist names.
- FR-013: The system shall allow local song title and artist display values to differ
  from remote metadata.
- FR-014: The system shall preserve local overrides across remote syncs.
- FR-015: The system shall keep remote metadata and local overrides distinguishable.

## Remote Sync

- FR-016: The system shall detect songs added to a remote playlist since the previous
  sync.
- FR-017: The system shall detect songs removed from a remote playlist since the
  previous sync.
- FR-018: The system shall detect remote playlist renames.
- FR-019: The system should detect remote track metadata changes when available.
- FR-020: The system shall report sync differences to the user before destructive or
  large local changes are applied.

## Local Environment Scanning

- FR-021: The system shall let the user select a local music folder or USB drive as an
  environment.
- FR-022: The system shall let the user create multiple named environments or
  workspaces.
- FR-023: The system shall link each environment to a USB drive, local folder, or volume
  identifier.
- FR-024: The system shall scan supported audio files in the selected environment.
- FR-025: The system shall store local file path, filename, extension, file size, and
  modification time.
- FR-026: The system should read embedded metadata tags when supported.
- FR-027: The system shall detect local audio files that are not present in any managed
  playlist.
- FR-028: The system should support importing local playlists or mappings from another
  environment in a later phase.

## Matching

- FR-029: The system shall attempt to match canonical songs to local audio files.
- FR-030: The system shall support exact matching by normalized title and artist.
- FR-031: The system should support duration-tolerant matching when duration is
  available.
- FR-032: The system should use filename heuristics as a fallback matching signal.
- FR-033: The system shall mark songs with no local audio match as missing audio.
- FR-034: The system shall mark multiple plausible local matches as ambiguous.
- FR-035: The system shall let the user manually map a canonical song to a local audio
  file.
- FR-036: The system shall preserve manual mappings across future scans and syncs.
- FR-037: The system shall provide a manual matching review workflow where the user can
  play local candidate audio before accepting a mapping.

## Playback

- FR-038: The system shall play matched local audio files for review.
- FR-039: The system shall indicate when playback is unavailable because a song has no
  matched local audio file.

## USB Organization and Export

- FR-040: The system shall export selected playlists to a USB-ready folder structure.
- FR-041: The system shall support a playlist-folder export layout.
- FR-042: The system shall support physical file duplication across playlist folders as
  the baseline export strategy.
- FR-043: The system should be designed to support reference-based or profile-specific
  export strategies later.
- FR-044: The system shall generate an export plan before writing changes.
- FR-045: The system shall apply planned export changes only after explicit user
  confirmation.
- FR-046: The system shall remove stale copies from app-managed playlist folders when a
  song disappears from the corresponding remote playlist.
- FR-047: The system shall avoid permanently deleting source audio files solely because
  they disappeared from a remote playlist.
- FR-048: The system shall preserve at least one copy of a removed song on the USB when
  it no longer belongs to any active managed playlist, using a dedicated deprecated
  folder.
- FR-049: The system shall notify the user how many songs were removed from active
  playlist folders and how many were preserved in the deprecated folder.
- FR-050: The system shall surface files that would become deprecated or unmanaged after
  export.

## DJ Metadata

- FR-051: The system should store BPM, musical key, cue points, comments, and other DJ
  metadata when available.
- FR-052: The system should keep DJ metadata independent from remote SoundCloud
  metadata.
- FR-053: The system should support ecosystem-specific metadata export profiles in a
  later phase.

## Dashboard

- FR-054: The system shall show playlist readiness based on matching and missing-audio
  status.
- FR-055: The system shall show missing audio per playlist.
- FR-056: The system shall show unmatched local files in the selected environment.
- FR-057: The system shall show ambiguous matches needing manual resolution.
- FR-058: The system should show duplicated playlist membership for songs appearing in
  multiple playlists.
- FR-059: The system shall show the current environment/workspace and linked USB or
  folder context.
