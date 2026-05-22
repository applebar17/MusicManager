# Product Vision

## Problem

DJ playlists may be curated remotely on SoundCloud while the playable audio files live
locally on a USB drive or another music folder. Keeping those two worlds aligned is
manual and error-prone:

- a SoundCloud playlist may include tracks that are missing locally;
- the same song may appear in multiple playlists;
- local filenames, titles, and artists may differ from SoundCloud metadata;
- USB folders may drift from the intended playlist structure;
- audio files may exist locally but not belong to any managed playlist.

## Product Idea

Music Manager is a local DJ library manager that mirrors remote SoundCloud playlists,
maps them to local audio files, and exports a USB-friendly organization for DJ
software and hardware.

The tool does not download audio from SoundCloud. It imports knowledge about playlists
and songs, then lets the user connect that knowledge to files they already own.

## Product Layers

1. Remote collection ingestion
   - Pull SoundCloud playlist data through API credentials or public playlist links.
   - Capture playlist membership, ordering, and available track metadata.

2. Canonical music library
   - Store unique song records once.
   - Store playlist membership as references to those unique songs.
   - Preserve remote data, local overrides, matching status, and sync state.

3. Local environment and USB export
   - Scan a USB drive or music folder for audio files.
   - Match local audio files to canonical songs.
   - Highlight missing, ambiguous, duplicate, and unmanaged files.
   - Reorganize or export the selected drive according to playlist structure and
     target profile rules.

## Primary User

The initial user is a DJ or music curator who:

- builds playlists on SoundCloud;
- maintains a local collection of playable audio files;
- prepares USB drives for sets;
- needs clear visibility into what is missing, duplicated, stale, or unmapped.

## Guiding Principles

- SoundCloud playlist data is remote knowledge, not playable audio.
- The app owns local curation, mappings, metadata overrides, and export settings.
- The internal library should deduplicate songs logically.
- The export layer may duplicate files physically when needed for compatibility.
- The tool should be safe by default and avoid irreversible file deletion.

