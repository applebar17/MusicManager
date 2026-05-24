import { useCallback, useEffect, useState } from "react";

import { EnvironmentPanel } from "../features/environments/EnvironmentPanel";
import { MatchingPanel } from "../features/matching/MatchingPanel";
import { PlaylistPanel } from "../features/playlists/PlaylistPanel";
import { ApiError, apiGet } from "../shared/api/http";
import type { HealthRead } from "../shared/api/types";
import { useAppState } from "../shared/state";
import { ErrorBanner, LoadingState } from "../shared/ui";

type BackendStatus =
  | { state: "checking" }
  | { state: "ready" }
  | { state: "unavailable"; message: string };

export function Dashboard() {
  const { activeView } = useAppState();
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
      {backendStatus.state === "checking" ? <LoadingState label="Checking backend" /> : null}
      {backendStatus.state === "unavailable" ? (
        <ErrorBanner
          title="Backend connection unavailable"
          message={backendStatus.message}
          actionLabel="Retry"
          onAction={checkBackend}
        />
      ) : null}
      {activeView === "playlists" ? (
        <PlaylistPanel />
      ) : activeView === "matching" ? (
        <MatchingPanel />
      ) : (
        <EnvironmentPanel />
      )}
    </div>
  );
}
