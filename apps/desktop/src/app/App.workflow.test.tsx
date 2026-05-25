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

    await user.click(screen.getByRole("button", { name: /playlists/i }));
    expect(await screen.findByText("No playlists imported yet")).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("SoundCloud playlist URL"),
      "https://soundcloud.com/demo/sets/wave-6-smoke",
    );
    await user.click(screen.getByRole("button", { name: /import \/ sync/i }));

    expect(await screen.findByText("Wave 6 Smoke")).toBeInTheDocument();
    expect(await screen.findByText("Smoke Track")).toBeInTheDocument();
    expect(screen.getByLabelText("SoundCloud playlist URL")).toHaveValue("");
    expect(screen.queryByText("soundcloud_api_enrichment_used")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^sync all$/i }));
    expect(await screen.findByText("Synced all")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /matching review/i }));
    expect(await screen.findByText("Resolve track mismatches and map ambiguous candidates.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /run matching/i }));
    expect(await screen.findByText("smoke-track-candidate.mp3")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /map file/i }));
    await waitFor(() => expect(screen.getByText("Manual")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /^export$/i }));
    await user.click(await screen.findByRole("button", { name: /preview export plan/i }));
    expect(await screen.findByText("Detailed Action Log")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^apply export plan$/i }));
    const dialog = screen.getByRole("dialog", { name: /apply this export plan/i });
    await user.click(within(dialog).getByRole("button", { name: /^apply export plan$/i }));

    expect(await screen.findByText("Export completed")).toBeInTheDocument();
    expect(screen.getByText("apply_1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /dashboard/i }));
    await user.click(screen.getByRole("button", { name: /^export$/i }));
    expect(await screen.findByText("Export completed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /refresh results/i }));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).endsWith("/environments/env_1/export-apply-runs/apply_1"),
        ),
      ).toBe(true),
    );
  });
});

function mockFetch() {
  let imported = false;
  let mapped = false;

  return (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), apiBaseUrl);
    const path = url.pathname;
    const method = init?.method ?? "GET";

    if (path === "/health" && method === "GET") {
      return jsonResponse({ status: "ok" });
    }

    if (path === "/environments" && method === "GET") {
      return jsonResponse([
        {
          archived_at: null,
          deprecated_folder_name: "_deprecated",
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

    if (path === "/environments/env_1/playlists/playlist_1" && method === "GET") {
      return jsonResponse({
        active_item_count: 1,
        environment_id: "env_1",
        id: "playlist_1",
        inactive_item_count: 0,
        items: [
          {
            accepted_audio_file_id: mapped ? "audio_1" : null,
            artist: "Smoke Artist",
            duration_seconds: 184,
            match_status: mapped ? "manually_mapped" : "ambiguous",
            playback_url: mapped ? "/environments/env_1/playback/audio-files/audio_1" : null,
            position: 1,
            remote_membership_active: true,
            song_id: "song_1",
            title: "Smoke Track",
          },
        ],
        name: "Wave 6 Smoke",
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
    title: "Smoke Track",
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
    items: [
      {
        action: "create_folder",
        reason: null,
        source_path: null,
        target_path: "/Volumes/USB/.music_manager",
      },
      {
        action: "create_folder",
        reason: null,
        source_path: null,
        target_path: "/Volumes/USB/Wave 6 Smoke",
      },
      {
        action: "copy_file",
        reason: null,
        source_path: "/Volumes/USB/smoke-track-candidate.mp3",
        target_path: "/Volumes/USB/Wave 6 Smoke/001 - Smoke Artist - Smoke Track.mp3",
      },
    ],
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
        source_path: null,
        status: "succeeded",
        target_path: "/Volumes/USB/Wave 6 Smoke",
      },
      {
        action: "copy_file",
        created_at: "2026-05-24T10:00:01+00:00",
        error_code: null,
        error_message: null,
        source_path: "/Volumes/USB/smoke-track-candidate.mp3",
        status: "succeeded",
        target_path: "/Volumes/USB/Wave 6 Smoke/001 - Smoke Artist - Smoke Track.mp3",
      },
    ],
    status: "completed",
  };
}
