# Decision 0002: Desktop Stack

## Status

Accepted during requirement gathering.

## Context

Music Manager needs deep local capabilities: USB access, folder scanning, local audio
playback, metadata reading, export planning, and safe filesystem writes. A browser-only
application would make these workflows harder.

The preferred implementation language mix is Python plus TypeScript.

## Decision

Build Music Manager as a desktop app using Tauri, TypeScript, and Python.

The expected split is:

- TypeScript frontend for the dashboard, workflows, and playback controls;
- Python backend for ingestion, scanning, matching, persistence, metadata handling, and
  export planning/apply;
- Tauri for desktop packaging and native filesystem integration.

## Consequences

Positive:

- Python is a strong fit for audio metadata, matching, local persistence, and later
  analysis tasks.
- TypeScript is a strong fit for a polished dashboard and review-heavy UI.
- Tauri keeps the desktop shell lighter than many alternatives.

Tradeoffs:

- Packaging a Python sidecar or backend with Tauri will require care.
- The app needs a clear boundary between frontend commands and backend operations.
- Early implementation should avoid over-investing in packaging details before the core
  workflows are proven.

