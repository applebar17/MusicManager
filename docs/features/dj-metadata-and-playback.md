# DJ Metadata and Playback

## Playback

The app should play matched local audio files so the user can verify mappings and
prepare playlists.

Playback should use local audio files only. SoundCloud playlist ingestion does not imply
streaming or downloading from SoundCloud.

Playback states:

- playable: the song has an accepted local file;
- missing: no local file is mapped;
- unavailable: the mapped file no longer exists;
- ambiguous: the user must choose which file to play.

## DJ Metadata

The app should eventually track DJ preparation metadata independently from SoundCloud
metadata.

Potential fields:

- BPM;
- musical key or tone;
- cue points;
- beat grid;
- genre;
- energy;
- comments;
- tags;
- rating or preparation status.

## Sources of DJ Metadata

DJ metadata may come from:

- embedded audio tags;
- manual user edits;
- analysis performed by the app;
- imports from DJ software;
- ecosystem-specific databases.

## MVP Position

Playback is useful in the MVP because it supports matching and review.

Automatic BPM, key detection, cue point editing, and DJ ecosystem metadata export should
be treated as later modules unless they become necessary for the first target export
environment.

## Ecosystem Compatibility

Different DJ tools store metadata differently. The app should avoid assuming that one
metadata model can be written directly to every target.

The recommended direction is:

- keep a neutral internal TrackAnalysis model;
- add export-profile adapters for specific consumers;
- show which metadata fields are supported by each export profile.

