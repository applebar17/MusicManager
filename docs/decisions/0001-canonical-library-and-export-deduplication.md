# Decision 0001: Canonical Library and Export Deduplication

## Status

Accepted during requirement gathering.

## Context

The same song may appear in multiple SoundCloud playlists. Internally duplicating that
song for every playlist would make metadata, matching, and local overrides harder to
maintain.

At the same time, many USB folder workflows and DJ devices expect files to exist in the
folder being browsed. A perfectly deduplicated physical USB layout may not work across
all DJ software and hardware.

## Decision

Music Manager should use logical deduplication internally and export-specific
duplication externally.

Internally:

- one SongMaster should represent one unique mix/version;
- playlists should reference SongMaster records;
- local metadata, mappings, and analysis should attach to the canonical song or its
  matched audio file.

Externally:

- the export profile decides whether files are duplicated, referenced, or represented
  in an ecosystem-specific database;
- the MVP will support physical duplication by playlist folder as the safest generic
  USB strategy.

## Consequences

Positive:

- local overrides and DJ metadata are maintained once per song;
- duplicate playlist membership is visible without duplicating library state;
- future export profiles can use more efficient strategies if the target supports them.

Tradeoffs:

- the first USB export may consume more drive space;
- export logic must translate from canonical library references to physical files;
- profile-specific compatibility research will be needed for advanced DJ ecosystems.

## Alternatives Considered

### Duplicate songs internally per playlist

Rejected for now because it makes matching, renaming, and metadata maintenance harder.

### Force one physical file on USB for all playlists

Deferred because generic DJ hardware and folder-based browsing may not support that
model reliably.
