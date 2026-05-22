# SoundCloud Ingestion

## Purpose

SoundCloud ingestion turns remote playlists into local playlist and song knowledge.
It does not download audio files.

## Import Modes

### Public playlist URL

The user provides one or more public SoundCloud playlist links.

The app should attempt to retrieve:

- playlist name;
- playlist URL;
- track list;
- track order;
- available track metadata.

This mode should work without user credentials when SoundCloud allows public access.

### API authentication

The user provides SoundCloud credentials or API keys.

The app should use an SDK or generated client based on the SoundCloud Swagger/OpenAPI
description when possible.

This mode may provide better access to:

- account playlists;
- private or authenticated data;
- stable remote IDs;
- richer metadata;
- refresh operations.

## Normalized Output

Both import modes should produce the same internal shape:

- Source;
- RemotePlaylist;
- remote track records;
- remote playlist membership and ordering;
- sync snapshot.

## Sync

The ingestion module should support refreshing known playlists and reporting:

- added songs;
- removed songs;
- reordered songs;
- renamed playlists;
- changed track metadata;
- unavailable tracks.

## Limitations to Track

- Public scraping or public URL resolution may be less stable than API access.
- SoundCloud metadata may not match local purchased or downloaded filenames.
- Remote tracks can disappear, become private, or change metadata.
- Remote track identity may not be enough to prove equality with a local audio file.
