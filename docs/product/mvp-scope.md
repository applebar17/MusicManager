# MVP Scope

The MVP should prove the core workflow: import remote playlist knowledge, match it to
local files, show gaps, and prepare a usable USB folder structure.

## Included in MVP

### Desktop app foundation

- Build a desktop app with a TypeScript frontend and Python backend running through
  Tauri.
- Use local-first storage and local filesystem access.
- Keep the early implementation compatible with a Python API/backend boundary so the
  product can iterate quickly before packaging details become the main constraint.

### Environments and workspaces

- Let the user create multiple music environments or workspaces.
- Link each environment to a USB drive, local folder, or volume identifier.
- Import and manage playlists inside an environment.
- Allow future import of local playlists or mappings from another environment.

### SoundCloud playlist import

- Import one or more SoundCloud playlists.
- Support public playlist URLs.
- Support API-based import if credentials and an SDK integration are available.
- Store playlist name, source URL or ID, track list, track ordering, and available
  track metadata.

### Canonical local library

- Create one master song record per unique track.
- Treat different mixes, edits, remixes, or versions as different canonical songs unless
  manually confirmed otherwise.
- Store playlist membership as references to master songs.
- Track which remote source produced each playlist and track.

### Local file scanning

- Let the user select a USB drive or local music environment.
- Scan audio files in that environment.
- Build local file records with path, filename, extension, size, and readable tags
  where available.

### Track matching

- Match remote song objects to local audio files.
- Start with title, artist, duration, and filename-based matching.
- Mark each song as matched, missing audio, ambiguous, or manually mapped.
- Let the user map a remote song to a specific unmatched local file.
- Provide a review workflow where local audio candidates can be played before a manual
  mapping is accepted.

### Local overrides

- Allow local renaming of playlists.
- Allow local display overrides for track title and artist.
- Preserve local overrides when remote playlists are synced again.

### Dashboard visibility

- Show songs present in remote playlists but missing local audio.
- Show audio files in the selected environment that are not present in any managed
  playlist.
- Show ambiguous matches that need manual resolution.
- Show playlist-level readiness for USB export.

### Playback

- Play matched local audio files from inside the app.
- Playback is for verification and preparation, not for SoundCloud streaming.

### USB export

- Export or reorganize a selected USB/music environment into playlist-based folders for
  the v1 generic USB folder mirror.
- Generate an export plan before writing changes.
- Apply the export plan only after the user confirms with an explicit button click.
- Remove stale copies from app-managed playlist folders when songs disappear from the
  corresponding remote playlists.
- Preserve at least one copy of removed audio by keeping it in another active playlist
  folder when still referenced, or moving/copying it into a deprecated folder when it no
  longer belongs to any active playlist.
- Notify the user how many songs were removed from active playlist folders and how many
  were preserved in the deprecated folder.
- Support physical duplication of files across playlist folders as the baseline
  compatibility mode.

## Deferred Features

- Automatic BPM analysis.
- Automatic musical key or tone detection.
- Cue point editing.
- Serato, Rekordbox, Pioneer, and other DJ ecosystem metadata export.
- Audio fingerprinting for advanced matching.
- Two-way sync back to SoundCloud.
- Multi-provider playlist ingestion beyond SoundCloud.
- Advanced conflict-resolution workflows.

## MVP Success Criteria

- A user can import playlists from SoundCloud.
- The app can tell which playlist tracks have local audio and which are missing.
- The user can manually fix incorrect or missing mappings.
- The user can identify local audio files that are outside all managed playlists.
- The user can generate a USB folder mirror that matches selected playlists.
- The user can preview and apply an export plan without losing the only available copy
  of a local audio file.
