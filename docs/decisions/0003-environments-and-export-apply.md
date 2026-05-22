# Decision 0003: Environments and Export Apply

## Status

Accepted during requirement gathering.

## Context

The user may prepare different USB drives or music folders for different contexts. The
tool should not assume there is only one global library/export target.

The export workflow also needs to be safe: remote playlist changes may remove songs
from playlist folders, but the app must not lose the only available audio copy.

## Decision

Music Manager should support multiple environments/workspaces. Each environment links
to a USB drive, local folder, or volume and owns its imported playlists, scan state,
mappings, export settings, and deprecated folder.

Export should be plan-based:

1. Generate a proposed export plan.
2. Show created folders, copied files, removed stale playlist copies, missing tracks,
   ambiguous tracks, and deprecated-folder actions.
3. Apply the plan only after explicit user confirmation.

When a song disappears from a remote playlist, export should remove stale copies from
the app-managed playlist folder. If the song no longer appears in any active managed
playlist, export should preserve at least one copy in the environment's deprecated
folder.

## Consequences

Positive:

- Different USB drives and preparation contexts can be managed cleanly.
- Export behavior is visible and confirmable before writes occur.
- Remote removals clean active playlist folders without deleting source audio.

Tradeoffs:

- The data model needs an environment/workspace boundary from the beginning.
- Export planning must distinguish app-managed folders from unrelated user files.
- The deprecated folder path and naming convention still need final definition.

