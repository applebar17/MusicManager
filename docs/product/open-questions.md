# Open Questions

These questions should be resolved before freezing implementation requirements.

## Settled Direction

- The first app shape is a desktop app.
- The selected stack is Python plus TypeScript in Tauri.
- The v1 export target is a generic USB folder mirror.
- Matching should be conservative by default.
- "Same song" means the same mix/version, not merely the same title and artist.
- The app should support multiple environments/workspaces.
- Export should produce a plan first and apply changes only after user confirmation.
- DJ metadata should stay light in v1.

## Product Decisions Still Open

- What exact environment/workspace fields are required in v1, such as name, linked USB
  volume ID, root folder, notes, and default export profile?
- Should cross-environment playlist import be included in v1 or treated as a near-term
  follow-up?
- Should the deprecated folder live at a fixed path on the USB, be configurable per
  environment, or both?

## SoundCloud Decisions

- Is API authentication available and stable enough for the first version?
- What playlist information can be reliably retrieved from public playlist URLs?
- How should the app behave if a playlist or track becomes private, deleted, or
  unavailable after a previous sync?

## Matching Decisions

- Which metadata fields are mandatory for a confident match?
- What confidence threshold should move a match from automatic to manual review?
- Should duration tolerance be strict, loose, or configurable?
- How should remixes, edits, bootlegs, and similarly named tracks be displayed in the
  review UI so that different versions are not merged accidentally?
- When should audio fingerprinting become necessary?

## USB and Export Decisions

- Should symlink or shortcut-based export ever be offered, given compatibility limits
  on USB drives and DJ hardware?
- Which filesystem constraints must be supported first, such as FAT32, exFAT, and
  forbidden filename characters?
- Should export operate directly on the linked USB or support an optional staging folder
  before final apply?
- What exact naming convention should the app use for the deprecated folder?

## Metadata Decisions

- Which audio formats should be supported first?
- Which tags should be read and written in the MVP?
- Should BPM, key, and cue points be edited in-app, imported from DJ software, or
  deferred until ecosystem-specific export profiles exist?
