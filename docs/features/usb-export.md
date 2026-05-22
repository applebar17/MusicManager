# USB Export

## Purpose

USB export turns the canonical library and accepted file mappings into a folder
structure that can be used by DJ software or hardware.

For v1, the target is a generic USB folder mirror.

## Baseline Export Strategy

The baseline MVP export strategy is physical duplication by playlist folder.

Example:

```text
USB_ROOT/
  Playlist A/
    Artist 1 - Track 1.mp3
    Artist 2 - Track 2.mp3
  Playlist B/
    Artist 1 - Track 1.mp3
    Artist 3 - Track 3.mp3
```

This wastes space when the same song appears in multiple playlists, but it is the most
compatible strategy for generic USB use.

## Internal vs External Deduplication

Internally, the app should deduplicate songs with SongMaster records.

Externally, the export strategy decides whether a file is:

- copied into every playlist folder;
- referenced from one shared master folder;
- represented through a DJ ecosystem database;
- skipped because the target profile cannot support it.

## Export Plan and Apply

Before writing changes, the app should generate an export plan. The plan should show:

- folders to create;
- files to copy;
- files that already exist;
- stale playlist-folder copies to remove;
- files to preserve in the deprecated folder;
- missing songs that cannot be exported;
- ambiguous songs requiring manual mapping;
- files that may become unmanaged or stale.

The user applies the plan with an explicit button click. Until then, scanning, syncing,
and planning are read-only with respect to the USB filesystem.

## Removed Remote Songs

If a song disappears from a remote playlist, the next export plan should remove stale
copies from that playlist's app-managed folder.

The app must still preserve at least one copy of the audio:

- if the song remains in another active playlist, that playlist copy can remain;
- if the song disappears from every active playlist, the export plan should move or copy
  one copy into the environment's deprecated folder;
- the original source audio file should not be permanently deleted by sync or normal
  export cleanup.

After apply, the app should notify the user how many stale playlist-folder copies were
removed and how many songs were preserved in the deprecated folder.

## Export Profiles

The first profile can be a generic folder mirror.

Later profiles may target:

- Rekordbox;
- Pioneer hardware workflows;
- Serato;
- other DJ software or hardware.

Each profile may define:

- folder layout;
- filename rules;
- metadata files;
- supported audio references;
- duplicate strategy;
- cue point and analysis compatibility.
