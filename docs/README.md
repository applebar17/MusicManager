# Music Manager Docs

This directory captures the current requirement-gathering knowledge for Music Manager.
The documents are drafts: they are meant to organize the product thinking before final
requirements and implementation plans are produced.

## Navigation

- [Product Vision](product/vision.md) - problem, goals, users, and product layers.
- [MVP Scope](product/mvp-scope.md) - proposed first version and deferred features.
- [Open Questions](product/open-questions.md) - decisions still to make.
- [Functional Requirements](requirements/functional-requirements.md) - draft feature requirements.
- [Non-Functional Requirements](requirements/non-functional-requirements.md) - quality and safety requirements.
- [Domain Model](domain/domain-model.md) - core entities and relationships.
- [Sync and Source of Truth](domain/sync-and-source-of-truth.md) - ownership of remote and local state.
- [Architecture Overview](architecture/overview.md) - proposed system layers and data flow.
- [Technology Stack](architecture/tech-stack.md) - selected desktop stack and implementation direction.
- [Scaffold Notes](development/scaffold.md) - current repository layout and layer boundaries.
- [SoundCloud Ingestion](features/soundcloud-ingestion.md) - playlist import and sync.
- [Local Library and Matching](features/local-library-and-matching.md) - matching remote tracks to local audio files.
- [USB Export](features/usb-export.md) - drive reorganization and duplicate handling.
- [DJ Metadata and Playback](features/dj-metadata-and-playback.md) - playback, BPM, key, cues, and ecosystem metadata.
- [Decision 0001](decisions/0001-canonical-library-and-export-deduplication.md) - canonical library with export-specific duplication.
- [Decision 0002](decisions/0002-desktop-stack.md) - Tauri desktop app with Python and TypeScript.
- [Decision 0003](decisions/0003-environments-and-export-apply.md) - environment/workspace model and export apply behavior.

## Current Product Shape

Music Manager is a local DJ library management tool that mirrors SoundCloud playlist
curation, matches those remote playlist tracks to local audio files, and exports a
USB-ready structure for DJ use.

The application should be a local desktop app. It should not download songs from
SoundCloud. It should create remote song objects, maintain a canonical local library,
highlight missing audio, support manual mappings, and reorganize a selected USB drive
or music environment safely.
