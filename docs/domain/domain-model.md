# Domain Model

The model separates remote playlist knowledge, canonical songs, local audio files, and
USB export state.

## Core Entities

### Source

Represents an origin of playlist knowledge.

Important fields:

- source type, such as SoundCloud API or SoundCloud public URL;
- account or owner identifier when available;
- credentials reference when API authentication is used;
- sync capability and limitations.

### RemotePlaylist

Represents a playlist as reported by a remote source.

Important fields:

- remote playlist ID or URL;
- remote name;
- source;
- last sync time;
- latest remote snapshot;
- remote track ordering.

### Playlist

Represents the user-facing playlist inside Music Manager.

Important fields:

- local playlist ID;
- linked remote playlist when applicable;
- local display name override;
- playlist items referencing canonical songs;
- ordering and export settings.
- environment/workspace association.

### SongMaster

Represents one canonical song known to the app. A canonical song represents a specific
mix/version. Different edits, remixes, bootlegs, or versions should remain separate
unless the user manually confirms a mapping.

Important fields:

- canonical song ID;
- remote identifiers and source references;
- imported title, artist, duration, and artwork where available;
- local title and artist overrides;
- matching status;
- DJ metadata references.

### PlaylistItem

Represents membership of a canonical song inside a playlist.

Important fields:

- playlist ID;
- canonical song ID;
- position;
- source membership status;
- added and removed timestamps when known.

### AudioFile

Represents a playable local file found in a music environment.

Important fields:

- file path;
- environment ID;
- filename and extension;
- file size;
- modification time;
- readable metadata tags;
- optional content hash or fingerprint later.

### MatchLink

Represents the relationship between a canonical song and a local audio file.

Important fields:

- song ID;
- audio file ID;
- match method, such as automatic, manual, exact metadata, filename, or fingerprint;
- confidence score;
- review status;
- created and updated timestamps.

### LocalOverride

Represents user-owned changes that should survive remote sync.

Important fields:

- target entity type, such as playlist or song;
- target ID;
- overridden field;
- override value;
- created and updated timestamps.

### LibrarySyncState

Represents what changed between remote syncs.

Important fields:

- source ID;
- remote playlist ID;
- previous sync snapshot;
- latest sync snapshot;
- detected additions, removals, renames, and metadata changes.

### MusicEnvironment

Represents a workspace that links playlist management to a USB drive, local folder, or
volume.

Important fields:

- environment ID;
- root path or volume identifier;
- environment name;
- linked USB or folder path;
- default export profile;
- deprecated folder path;
- last scan time;
- file inventory.

### ExportTarget

Represents a destination for writing playlist structure.

Important fields:

- target path or volume identifier;
- export profile;
- selected playlists;
- selected export strategy;
- last export plan and result.

### ExportPlan

Represents a proposed set of filesystem changes before they are applied.

Important fields:

- environment ID;
- export target ID;
- generated timestamp;
- planned folder creations;
- planned file copies;
- planned removals from app-managed playlist folders;
- planned moves or copies into the deprecated folder;
- skipped items and reasons;
- user confirmation state;
- apply result.

### TrackAnalysis

Represents DJ-oriented metadata that may be imported, edited, or computed.

Important fields:

- song ID or audio file ID;
- BPM;
- musical key;
- cue points;
- beat grid references;
- comments, genre, energy, and tags.

## Important Relationships

- One Source can provide many RemotePlaylists.
- One RemotePlaylist can be linked to one local Playlist.
- One MusicEnvironment can contain many Playlists.
- One Playlist contains many PlaylistItems.
- One PlaylistItem references one SongMaster.
- One SongMaster can appear in many playlists.
- One SongMaster may be linked to zero, one, or many candidate AudioFiles.
- One accepted MatchLink identifies the current playable local file for a SongMaster.
- One MusicEnvironment contains many AudioFiles.
- One ExportTarget uses playlists and match links to generate a USB structure.
- One ExportTarget can generate many ExportPlans over time.

## Identity Strategy

Canonical identity should be conservative. The app should merge remote tracks into the
same SongMaster only when it has enough evidence that they represent the same
mix/version. When confidence is low, the app should keep separate SongMaster records
and surface the possible duplicate for review.
