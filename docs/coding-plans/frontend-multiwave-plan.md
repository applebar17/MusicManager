# Frontend Multiwave Plan

## Purpose

This plan implements the desktop frontend after the backend API has reached the first
desktop-ready contract. The goal is to turn the existing Tauri + React scaffold into a
usable local DJ library management UI for creating environments, importing playlists,
reviewing matches, previewing export plans, and applying USB mirror exports.

The frontend should stay thin: it should orchestrate backend workflows, present clear
review states, and avoid duplicating backend matching/export logic.

## Frontend Principles

- Keep the existing feature-oriented structure under `apps/desktop/src/features/`.
- Use typed API clients at the frontend/backend boundary.
- Build the actual app workflow, not a marketing landing page.
- Prefer dense, scan-friendly operational UI over decorative layouts.
- Keep filesystem-changing actions explicit, previewed, and confirmed.
- Avoid storing backend-derived state permanently in the frontend.
- Add tests or typed checks for every wave that changes behavior.

## Wave 0: Frontend Foundation and API Contract

Goal: make the desktop scaffold reliable and ready to consume the backend API.

Deliverables:

- Confirm React, Vite, TypeScript, Tauri, and workspace scripts run cleanly.
- Keep the desktop toolchain on Node 20 or newer; use a containerized Node 20
  environment when local machines cannot run that version.
- Expand the shared HTTP client with `GET`, `POST`, `PATCH`, typed request/response
  helpers, backend error parsing, and configurable API base URL.
- Add TypeScript types matching Wave 10 backend DTOs.
- Add a small app state model for selected environment and selected playlist.
- Add loading, empty, and error UI primitives.
- Keep the existing feature folders and avoid large all-in-one components.

Suggested modules:

- `src/shared/api/http.ts`
- `src/shared/api/types.ts`
- `src/shared/state/`
- `src/shared/ui/`
- `src/app/AppShell.tsx`

Tests:

- TypeScript build passes.
- API client parses success and `{ code, message }` backend errors.
- App shell renders without a backend connection and shows a recoverable error state.

Exit criteria:

- A developer can run the desktop app and see a stable shell that is ready to connect
  to backend data.

## Wave 0.5: Design System Intake

Goal: translate the design pages in `docs/product/design/DESIGN.md` into reusable
frontend primitives before feature-heavy Wave 1 work begins.

Deliverables:

- Treat `DESIGN.md` as the first visual source of truth for the desktop app.
- Add CSS custom properties and TypeScript token exports for the dark Precision Audio
  Utility palette, 4px spacing rhythm, compact typography, and precise radii.
- Add shared UI primitives for panels, panel headers, buttons, badges, loading, empty,
  and error states.
- Align the app shell, sidebar, feature placeholders, and status treatments with the
  design language.
- Keep the design layer thin and practical; defer a full component library until real
  feature screens need it.

Suggested modules:

- `src/shared/design/`
- `src/shared/ui/`
- `src/styles.css`
- `src/app/AppShell.tsx`

Tests:

- TypeScript checks pass.
- Shared primitives can be imported from `src/shared/ui`.
- The desktop shell still renders without requiring backend data.

Exit criteria:

- Wave 1 can build real environment UI using shared design tokens and primitives
  instead of one-off styles.

## Wave 1: Environment Dashboard

Goal: let the user create/select an environment and see backend readiness at a glance.

Deliverables:

- List environments and select the active environment.
- Create, update, and archive environments using backend routes.
- Use Tauri folder selection for root paths when running inside the desktop shell,
  with a manual path fallback for browser development.
- Trigger scan for the selected environment.
- Show environment overview counts from `GET /environments/{id}/overview`.
- Show active, removed, and unmanaged audio-file summaries.

Suggested modules:

- `features/environments/`
- `features/library/`
- `shared/tauri/dialogs.ts`

Tests:

- Environment list/create/update/archive flows call the expected API paths.
- Scan updates overview counts.
- Folder picker fallback works when Tauri APIs are unavailable.
- Empty environment state is clear and actionable.

Exit criteria:

- The user can create a workspace, connect it to a folder or USB path, scan it, and
  understand the local library status.

## Wave 2: Playlist Import and Playlist Browser

Goal: let the user import SoundCloud playlists and inspect playlist readiness.

Deliverables:

- Add SoundCloud public playlist URL import form.
- Show import result counts and parser warnings.
- List playlists from `GET /environments/{id}/playlists`.
- Show playlist detail from `GET /environments/{id}/playlists/{playlist_id}`.
- Highlight active vs inactive playlist membership.
- Show per-track match status, accepted audio file, and playback link when available.

Suggested modules:

- `features/playlists/`
- `features/soundcloud/`
- `shared/ui/status-badges.tsx`

Tests:

- URL import posts to the backend and refreshes playlist views.
- Playlist list displays matched, missing, ambiguous, and manually mapped counts.
- Playlist detail preserves track order and membership state.
- Import warnings are visible without blocking the workflow.

Exit criteria:

- The user can import a playlist and understand which tracks are ready, missing, or
  need review.

## Wave 3: Matching Review and Playback

Goal: provide a useful manual-review workspace for missing and ambiguous audio.

Deliverables:

- Run matching for the selected environment.
- Display review rows from `GET /environments/{id}/matching/review`.
- Filter review by `matched`, `missing_audio`, `ambiguous`, and `manually_mapped`.
- Let the user play candidate and accepted audio files through the playback endpoint.
- Let the user create manual mappings.
- Refresh overview, playlist detail, and review rows after manual mapping.

Suggested modules:

- `features/matching/`
- `features/playback/`
- `shared/audio/`

Tests:

- Matching run refreshes review and playlist readiness.
- Candidate playback uses backend playback URLs.
- Manual mapping posts the selected song/audio pair and updates row status.
- Removed or unavailable files show a readable error.

Exit criteria:

- The user can resolve ambiguous tracks by listening to candidates and saving manual
  mappings.

## Wave 4: Export Plan Preview

Goal: let the user preview USB mirror changes before any filesystem writes.

Deliverables:

- Create export plans for all playlists or selected playlists.
- Display export plan counts grouped by action.
- Show planned folders, copies, stale removals, deprecated preserves, and skips.
- Make missing/ambiguous skipped tracks obvious and link them back to review.
- Require explicit confirmation before applying a plan.
- Keep export plan creation separate from export apply.

Suggested modules:

- `features/export/`
- `features/export/ExportPlanPreview.tsx`
- `features/export/ExportActionList.tsx`

Tests:

- Plan creation posts selected playlist IDs correctly.
- Preview groups and labels all export actions.
- Apply button is disabled or confirmed until the user reviews the plan.
- Skipped items are visible with backend reasons.

Exit criteria:

- The user can review exactly what will happen to the managed USB export folder before
  applying changes.

## Wave 5: Export Apply and Results

Goal: let the user apply a confirmed plan and inspect results safely.

Deliverables:

- Apply a persisted export plan through the backend apply endpoint.
- Show apply status, success/failure/skipped counts, and per-item results.
- Fetch persisted apply runs by ID.
- Keep successful apply results visible after navigation.
- Show partial failures without hiding successful writes.
- Encourage creating a fresh plan after meaningful library changes.

Suggested modules:

- `features/export/ExportApplyPanel.tsx`
- `features/export/ExportApplyResults.tsx`

Tests:

- Apply posts to the expected plan endpoint and renders results.
- Persisted apply-run lookup displays the same result data.
- Partial failures are readable and do not look like total success.
- Reapplying an already applied plan is represented as an explicit user action.

Exit criteria:

- The user can safely commit a reviewed USB mirror export and understand what happened.

## Wave 6: Desktop Polish and Workflow Hardening

Goal: make the first full desktop slice pleasant and resilient enough for daily use.

Deliverables:

- Add a cohesive navigation model for Dashboard, Playlists, Matching, and Export.
- Add persistent selected environment/playlist preferences.
- Improve empty/loading/error states across all panels.
- Add keyboard-friendly controls for review-heavy matching workflows.
- Add large-list ergonomics: search, filters, and basic virtualization only where needed.
- Review responsive behavior for the Tauri minimum window size.

Suggested modules:

- `src/app/navigation.ts`
- `src/shared/preferences/`
- `src/shared/ui/`

Tests:

- Build passes.
- Main workflow smoke test with mocked backend responses passes.
- Selected environment/playlist preferences restore correctly.
- UI remains usable at the configured minimum desktop window size.

Exit criteria:

- The frontend supports the full v1 workflow against the backend: create environment,
  scan, import playlist, review matches, preview export, and apply export.

## Deferred Frontend Work

- Background job progress UI for long scans/imports/exports.
- Rich audio waveform/cue-point editing.
- BPM/key editing and DJ ecosystem metadata views.
- Multi-provider imports beyond SoundCloud.
- Advanced table virtualization and pagination for very large libraries.
- Full design system extraction beyond the components needed for v1.
