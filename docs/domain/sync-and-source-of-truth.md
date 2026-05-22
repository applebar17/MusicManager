# Sync and Source of Truth

## Recommended Ownership Rule

SoundCloud is the source of truth for remote playlist membership.
Music Manager is the source of truth for local naming, local file mappings, DJ
metadata, playback availability, environments/workspaces, and export settings.

This keeps remote sync understandable while allowing the local library to become more
useful than a raw mirror.

## Remote-Owned Data

Remote-owned data includes:

- playlist source URL or remote ID;
- remote playlist name;
- remote track list;
- remote track ordering;
- remote title, artist, duration, artwork, and other available metadata;
- remote availability status.

Remote-owned data may change on refresh.

## Local-Owned Data

Local-owned data includes:

- local playlist display names;
- local song title and artist overrides;
- manual mappings from songs to local files;
- chosen export profile and export settings;
- environment/workspace definitions and linked USB or folder paths;
- DJ metadata added or curated locally;
- notes, tags, and preparation status.

Local-owned data should survive remote refreshes.

## Sync Behavior

On remote refresh, the system should:

1. Fetch the current remote playlist snapshot.
2. Compare it with the previous snapshot.
3. Detect added tracks, removed tracks, reorders, playlist renames, and metadata
   changes.
4. Update remote-owned fields.
5. Preserve local-owned fields.
6. Recalculate readiness, missing-audio status, and export impact.

## Removal Policy

If a track disappears from a remote playlist, the app should remove or mark the
playlist membership as inactive for that playlist. During export apply, stale file
copies should be removed from app-managed folders for playlists where the track no
longer belongs. The app should not permanently delete the source audio file or the
canonical song.

If the removed song still belongs to another active playlist, that active playlist copy
is enough to preserve it on the USB. If the removed song no longer belongs to any active
playlist, export should preserve at least one copy in the environment's deprecated
folder and notify the user.

A SongMaster can become:

- active: present in at least one managed playlist;
- deprecated: not present in any current playlist but retained in a dedicated
  environment folder for safety;
- unmanaged local file: a local audio file that is not matched to any active managed
  song.

## Conflict Examples

- Remote playlist renamed, but the user has a local playlist name override.
- Remote title changed, but the user has a local title override.
- A remote track was removed, but the matched local file still exists on USB.
- Two remote tracks look similar and both point to the same local file candidate.
- One remote track has multiple plausible local audio files.

## Conflict Handling Principle

The app should prefer visibility and manual review over silent destructive changes.
When in doubt, mark the item as changed, ambiguous, missing, deprecated, or unmanaged
and let the user choose the final mapping or export action.
