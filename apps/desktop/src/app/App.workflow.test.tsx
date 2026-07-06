import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const apiBaseUrl = "http://127.0.0.1:8000";
const preferencesKey = "music-manager.preferences.v1";

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(data), {
      headers: { "Content-Type": "application/json" },
      status,
    }),
  );
}

describe("desktop v1 workflow", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem(
      preferencesKey,
      JSON.stringify({
        selectedEnvironmentId: "env_1",
        selectedPlaylistId: null,
        selectedExportPlanId: null,
        selectedExportApplyRunId: null,
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("imports, matches, manually maps, plans export, applies export, and reads persisted results", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(mockFetch());
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Environment Overview")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^library$/i }));
    expect(await screen.findByText("Source of truth")).toBeInTheDocument();
    expect(screen.getByText("Not set")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Root path"), "/Users/demo/Music Library");
    await user.click(screen.getByRole("button", { name: /save library/i }));
    expect(await screen.findByText("Ready")).toBeInTheDocument();
    expect(await screen.findByText("Current library: /Users/demo/Music Library")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /dashboard/i }));

    await user.click(screen.getByRole("button", { name: /playlists/i }));
    expect(await screen.findByText("No playlists imported yet")).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("SoundCloud playlist URL"),
      "https://soundcloud.com/demo/sets/wave-6-smoke",
    );
    await user.click(screen.getByRole("button", { name: /import \/ sync/i }));

    expect((await screen.findAllByText("Wave 6 Smoke")).length).toBeGreaterThan(0);
    expect(await screen.findByText("Smoke Track")).toBeInTheDocument();
    expect(screen.getByLabelText("SoundCloud playlist URL")).toHaveValue("");
    expect(screen.queryByText("soundcloud_api_enrichment_used")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^sync playlist$/i }));
    expect(await screen.findByText("Synced")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^sync all$/i }));
    expect(await screen.findByText("Synced all")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /matching review/i }));
    expect(await screen.findByText("Resolve track mismatches and map ambiguous candidates.")).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /match downloads/i })).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: /match downloads/i }));
    expect(await screen.findByText("Downloads Matched")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /run matching/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /map file/i })).toBeEnabled());

    await user.click(screen.getByRole("button", { name: /map file/i }));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).endsWith("/environments/env_1/matching/manual-mappings"),
        ),
      ).toBe(true),
    );

    await user.click(screen.getByRole("button", { name: /^export$/i }));
    await user.click(await screen.findByRole("button", { name: /preview export plan/i }));
    expect(await screen.findByText("Filesystem Changes")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^apply export plan$/i }));
    const dialog = screen.getByRole("dialog", { name: /apply this export plan/i });
    await user.click(within(dialog).getByRole("button", { name: /^apply export plan$/i }));

    expect(await screen.findByText("This plan is locked after apply.")).toBeInTheDocument();
    expect(screen.getAllByText("Succeeded").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /dashboard/i }));
    await user.click(screen.getByRole("button", { name: /^export$/i }));
    expect(await screen.findByText("This plan is locked after apply.")).toBeInTheDocument();
  });
});

function mockFetch() {
  let imported = false;
  let mapped = false;
  let libraryRootPath: string | null = null;

  return (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), apiBaseUrl);
    const path = url.pathname;
    const method = init?.method ?? "GET";

    if (path === "/health" && method === "GET") {
      return jsonResponse({ status: "ok" });
    }

    if (path === "/library" && method === "GET") {
      return jsonResponse(libraryResponse(libraryRootPath));
    }

    if (path === "/library/alignment-runs/latest" && method === "GET") {
      return jsonResponse(null);
    }

    if (path === "/library/metadata/import-runs/latest" && method === "GET") {
      return jsonResponse(null);
    }

    if (path === "/library" && method === "PUT") {
      const body = JSON.parse(String(init?.body ?? "{}")) as { root_path: string };
      libraryRootPath = body.root_path;
      return jsonResponse(libraryResponse(libraryRootPath));
    }

    if (path === "/environments" && method === "GET") {
      return jsonResponse([
        {
          archived_at: null,
          deprecated_folder_name: "_deprecated",
          download_path: "/Users/demo/Downloads",
          id: "env_1",
          name: "USB Smoke",
          root_path: "/Volumes/USB",
        },
      ]);
    }

    if (path === "/environments/env_1/overview" && method === "GET") {
      return jsonResponse({
        active_audio_file_count: 1,
        active_playlist_item_count: imported ? 1 : 0,
        ambiguous_count: imported && !mapped ? 1 : 0,
        environment_id: "env_1",
        inactive_playlist_item_count: 0,
        manually_mapped_count: mapped ? 1 : 0,
        matched_count: mapped ? 1 : 0,
        missing_audio_count: 0,
        playlist_count: imported ? 1 : 0,
        removed_audio_file_count: 0,
        unmanaged_audio_file_count: 0,
        unique_song_count: imported ? 1 : 0,
      });
    }

    if (path === "/environments/env_1/audio-files" && method === "GET") {
      return jsonResponse([]);
    }

    if (path === "/environments/env_1/unmanaged-files" && method === "GET") {
      return jsonResponse([]);
    }

    if (path === "/environments/env_1/playlists" && method === "GET") {
      return jsonResponse(imported ? [playlistSummary(mapped)] : []);
    }

    if (path === "/environments/env_1/soundcloud/playlists" && method === "POST") {
      imported = true;
      return jsonResponse({
        added: 1,
        environment_id: "env_1",
        metadata_changed: 0,
        playlist_id: "playlist_1",
        playlist_name: "Wave 6 Smoke",
        reactivated: 0,
        remote_playlist_id: "remote_1",
        removed: 0,
        reordered: 0,
        sync_snapshot_id: "snapshot_1",
        track_count: 1,
        unchanged: 0,
        warnings: ["soundcloud_api_enrichment_used"],
      });
    }

    if (path === "/environments/env_1/soundcloud/playlists/sync-all" && method === "POST") {
      imported = true;
      return jsonResponse({
        environment_id: "env_1",
        failed: 0,
        results: [
          {
            added: 0,
            error_code: null,
            error_message: null,
            metadata_changed: 0,
            playlist_id: "playlist_1",
            playlist_name: "Wave 6 Smoke",
            reactivated: 0,
            remote_playlist_id: "remote_1",
            removed: 0,
            reordered: 0,
            source_url: "https://soundcloud.com/demo/sets/wave-6-smoke",
            status: "synced",
            track_count: 1,
            unchanged: 1,
            warnings: [],
          },
        ],
        succeeded: 1,
        total: 1,
      });
    }

    if (path === "/environments/env_1/soundcloud/playlists/playlist_1/sync" && method === "POST") {
      imported = true;
      return jsonResponse({
        added: 0,
        environment_id: "env_1",
        metadata_changed: 1,
        playlist_id: "playlist_1",
        playlist_name: "Wave 6 Smoke",
        reactivated: 0,
        remote_playlist_id: "remote_1",
        removed: 0,
        reordered: 0,
        sync_snapshot_id: "snapshot_2",
        track_count: 1,
        unchanged: 1,
        warnings: [],
      });
    }

    if (path === "/environments/env_1/playlists/playlist_1" && method === "GET") {
      return jsonResponse({
        active_item_count: 1,
        environment_id: "env_1",
        id: "playlist_1",
        inactive_item_count: 0,
        items: [
          {
            accepted_audio_file_id: mapped ? "audio_1" : null,
            accepted_audio_warnings: [],
            artist: "Smoke Artist",
            duration_seconds: 184,
            local_membership_active: false,
            added_by_local_audio_file_id: null,
            match_status: mapped ? "manually_mapped" : "ambiguous",
            playback_url: mapped ? "/environments/env_1/playback/audio-files/audio_1" : null,
            position: 1,
            remote_removed_at: null,
            remote_membership_active: true,
            song_id: "song_1",
            title: "Smoke Track",
          },
        ],
        name: "Wave 6 Smoke",
        removed_items: [],
        remote_playlist_id: "remote_1",
      });
    }

    if (path === "/environments/env_1/matching/run" && method === "POST") {
      return jsonResponse({
        ambiguous: mapped ? 0 : 1,
        environment_id: "env_1",
        manually_mapped: mapped ? 1 : 0,
        matched: mapped ? 1 : 0,
        missing_audio: 0,
        total: 1,
      });
    }

    if (path === "/environments/env_1/matching/downloads/run" && method === "POST") {
      return jsonResponse({
        download_path: "/Users/demo/Downloads",
        environment_id: "env_1",
        matching: {
          ambiguous: mapped ? 0 : 1,
          checked: 1,
          matched: mapped ? 1 : 0,
          missing_audio: 0,
          preserved_reviewed: 0,
        },
        scan: {
          added: 1,
          changed: 0,
          environment_id: "env_1",
          moved: 0,
          removed: 0,
          scan_run_id: "scan_downloads_1",
          total_active: 1,
          unchanged: 0,
        },
      });
    }

    if (path === "/environments/env_1/matching/review" && method === "GET") {
      return jsonResponse([
        {
          artist: "Smoke Artist",
          candidates: mapped ? [] : [candidate()],
          duration_seconds: 184,
          match: mapped ? candidate() : null,
          song_id: "song_1",
          status: mapped ? "manually_mapped" : "ambiguous",
          title: "Smoke Track",
        },
      ]);
    }

    if (path === "/environments/env_1/matching/manual-mappings" && method === "POST") {
      mapped = true;
      return jsonResponse({
        ambiguous: 0,
        environment_id: "env_1",
        manually_mapped: 1,
        matched: 1,
        missing_audio: 0,
        total: 1,
      });
    }

    if (path === "/environments/env_1/export-plans" && method === "POST") {
      return jsonResponse(exportPlan());
    }

    if (path === "/environments/env_1/export-plans/plan_1" && method === "GET") {
      return jsonResponse(exportPlan());
    }

    if (path === "/environments/env_1/export-plans/plan_1" && method === "PATCH") {
      return jsonResponse(exportPlan());
    }

    if (path === "/environments/env_1/export-plans/plan_1/apply" && method === "POST") {
      return jsonResponse(applyRun());
    }

    if (path === "/environments/env_1/export-apply-runs/apply_1" && method === "GET") {
      return jsonResponse(applyRun());
    }

    return jsonResponse({ code: "not_found", message: `Unhandled ${method} ${path}` }, 404);
  };
}

function playlistSummary(mapped: boolean) {
  return {
    active_item_count: 1,
    ambiguous_count: mapped ? 0 : 1,
    id: "playlist_1",
    inactive_item_count: 0,
    manually_mapped_count: mapped ? 1 : 0,
    matched_count: mapped ? 1 : 0,
    missing_audio_count: 0,
    name: "Wave 6 Smoke",
    remote_playlist_id: "remote_1",
  };
}

function candidate() {
  return {
    artist: "Smoke Artist",
    audio_file_id: "audio_1",
    confidence: 0.88,
    duration_seconds: 184,
    method: "title_duration",
    path: "/Volumes/USB/smoke-track-candidate.mp3",
    source_area: "download",
    title: "Smoke Track",
    warnings: [],
  };
}

function exportPlan() {
  return {
    counts: {
      copy_file: 1,
      create_folder: 2,
    },
    environment_id: "env_1",
    export_plan_id: "plan_1",
    is_valid: true,
    locked_at: null,
    validation_error_code: null,
    validation_error_message: null,
    validation_errors: [],
    items: [
      {
        action: "create_folder",
        export_plan_item_id: "item_1",
        included: true,
        position: 0,
        reason: null,
        source_path: null,
        target_path: "/Volumes/USB/_music_manager",
        validation_error_code: null,
        validation_error_message: null,
      },
      {
        action: "create_folder",
        export_plan_item_id: "item_2",
        included: true,
        position: 1,
        reason: null,
        source_path: null,
        target_path: "/Volumes/USB/Wave 6 Smoke",
        validation_error_code: null,
        validation_error_message: null,
      },
      {
        action: "copy_file",
        export_plan_item_id: "item_3",
        included: true,
        position: 2,
        reason: null,
        source_path: "/Volumes/USB/smoke-track-candidate.mp3",
        target_path: "/Volumes/USB/Wave 6 Smoke/smoke-track-candidate.mp3",
        validation_error_code: null,
        validation_error_message: null,
      },
    ],
  };
}

function libraryResponse(rootPath: string | null) {
  return {
    configured: rootPath !== null,
    created_at: rootPath === null ? null : "2026-07-06T10:00:00+00:00",
    last_metadata_imported_at: null,
    metadata_asset_count: 0,
    metadata_index_entry_count: 0,
    missing_track_count: 0,
    root_path: rootPath,
    track_count: 0,
    updated_at: rootPath === null ? null : "2026-07-06T10:00:00+00:00",
  };
}

function applyRun() {
  return {
    apply_run_id: "apply_1",
    counts: {
      succeeded: 2,
    },
    environment_id: "env_1",
    export_plan_id: "plan_1",
    item_results: [
      {
        action: "create_folder",
        created_at: "2026-05-24T10:00:00+00:00",
        error_code: null,
        error_message: null,
        export_plan_item_id: "item_2",
        source_path: null,
        status: "succeeded",
        target_path: "/Volumes/USB/Wave 6 Smoke",
      },
      {
        action: "copy_file",
        created_at: "2026-05-24T10:00:01+00:00",
        error_code: null,
        error_message: null,
        export_plan_item_id: "item_3",
        source_path: "/Volumes/USB/smoke-track-candidate.mp3",
        status: "succeeded",
        target_path: "/Volumes/USB/Wave 6 Smoke/smoke-track-candidate.mp3",
      },
    ],
    status: "completed",
  };
}
