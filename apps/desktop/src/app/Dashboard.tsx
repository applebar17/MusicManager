import { useCallback, useEffect, useState } from "react";

import { EnvironmentPanel } from "../features/environments/EnvironmentPanel";
import { ExportPanel } from "../features/export/ExportPanel";
import { MatchingPanel } from "../features/matching/MatchingPanel";
import { PlaybackPanel } from "../features/playback/PlaybackPanel";
import { PlaylistPanel } from "../features/playlists/PlaylistPanel";
import { ApiError, apiGet } from "../shared/api/http";
import type { HealthRead } from "../shared/api/types";
import { ErrorBanner, LoadingState, StatusBadge } from "../shared/ui";

type BackendStatus =
  | { state: "checking" }
  | { state: "ready" }
  | { state: "unavailable"; message: string };

export function Dashboard() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ state: "checking" });

  const checkBackend = useCallback(() => {
    setBackendStatus({ state: "checking" });
    void apiGet<HealthRead>("/health")
      .then(() => {
        setBackendStatus({ state: "ready" });
      })
      .catch((error: unknown) => {
        setBackendStatus({
          state: "unavailable",
          message:
            error instanceof ApiError
              ? error.message
              : "The backend is not reachable at the configured API URL.",
        });
      });
  }, []);

  useEffect(() => {
    checkBackend();
  }, [checkBackend]);

  return (
    <div className="stack">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Desktop workspace</p>
          <h2>Backend-ready library cockpit</h2>
          <p className="muted">
            Wave 0 prepares the shell, API contract, and app state for the first
            connected workflow.
          </p>
        </div>
        {backendStatus.state === "checking" ? (
          <LoadingState label="Checking backend" />
        ) : (
          <StatusBadge tone={backendStatus.state === "ready" ? "success" : "danger"}>
            {backendStatus.state === "ready" ? "Backend ready" : "Backend offline"}
          </StatusBadge>
        )}
      </header>
      {backendStatus.state === "unavailable" ? (
        <ErrorBanner
          title="Backend connection unavailable"
          message={backendStatus.message}
          actionLabel="Retry"
          onAction={checkBackend}
        />
      ) : null}
      <EnvironmentPanel />
      <PlaylistPanel />
      <MatchingPanel />
      <PlaybackPanel />
      <ExportPanel />
    </div>
  );
}
