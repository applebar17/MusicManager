import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { loadPreferences, savePreferences } from "../preferences";

export type AppView =
  | "dashboard"
  | "library"
  | "playlists"
  | "usb"
  | "matching"
  | "export"
  | "settings";

type AppSelection = {
  activeView: AppView;
  selectedEnvironmentId: string | null;
  selectedPlaylistId: string | null;
  selectedExportPlanId: string | null;
  selectedExportApplyRunId: string | null;
  focusedLibraryTrackId: string | null;
};

type AppStateContextValue = AppSelection & {
  selectView: (view: AppView) => void;
  selectEnvironment: (environmentId: string | null) => void;
  selectPlaylist: (playlistId: string | null) => void;
  selectExportPlan: (exportPlanId: string | null) => void;
  selectExportApplyRun: (applyRunId: string | null) => void;
  openLibraryTrack: (libraryTrackId: string) => void;
  clearFocusedLibraryTrack: () => void;
};

const AppStateContext = createContext<AppStateContextValue | null>(null);

type AppStateProviderProps = {
  children: ReactNode;
};

export function AppStateProvider({ children }: AppStateProviderProps) {
  const preferences = useMemo(() => loadPreferences(), []);
  const [selection, setSelection] = useState<AppSelection>({
    activeView: "dashboard",
    selectedEnvironmentId: preferences.selectedEnvironmentId,
    selectedPlaylistId: preferences.selectedPlaylistId,
    selectedExportPlanId: preferences.selectedExportPlanId,
    selectedExportApplyRunId: preferences.selectedExportApplyRunId,
    focusedLibraryTrackId: null,
  });

  useEffect(() => {
    savePreferences({
      selectedEnvironmentId: selection.selectedEnvironmentId,
      selectedPlaylistId: selection.selectedPlaylistId,
      selectedExportPlanId: selection.selectedExportPlanId,
      selectedExportApplyRunId: selection.selectedExportApplyRunId,
    });
  }, [
    selection.selectedEnvironmentId,
    selection.selectedExportApplyRunId,
    selection.selectedExportPlanId,
    selection.selectedPlaylistId,
  ]);

  const value = useMemo<AppStateContextValue>(
    () => ({
      ...selection,
      selectView: (view) => {
        setSelection((current) =>
          current.activeView === view ? current : { ...current, activeView: view },
        );
      },
      selectEnvironment: (environmentId) => {
        setSelection((current) =>
          current.selectedEnvironmentId === environmentId && current.selectedPlaylistId === null
            ? current
            : {
                ...current,
                selectedEnvironmentId: environmentId,
                selectedPlaylistId: null,
                selectedExportPlanId: null,
                selectedExportApplyRunId: null,
              },
        );
      },
      selectPlaylist: (playlistId) => {
        setSelection((current) =>
          current.selectedPlaylistId === playlistId
            ? current
            : { ...current, selectedPlaylistId: playlistId },
        );
      },
      selectExportPlan: (exportPlanId) => {
        setSelection((current) =>
          current.selectedExportPlanId === exportPlanId
            ? current
            : {
                ...current,
                selectedExportPlanId: exportPlanId,
                selectedExportApplyRunId: null,
              },
        );
      },
      selectExportApplyRun: (applyRunId) => {
        setSelection((current) =>
          current.selectedExportApplyRunId === applyRunId
            ? current
            : { ...current, selectedExportApplyRunId: applyRunId },
        );
      },
      openLibraryTrack: (libraryTrackId) => {
        setSelection((current) => ({
          ...current,
          activeView: "library",
          focusedLibraryTrackId: libraryTrackId,
        }));
      },
      clearFocusedLibraryTrack: () => {
        setSelection((current) =>
          current.focusedLibraryTrackId === null
            ? current
            : { ...current, focusedLibraryTrackId: null },
        );
      },
    }),
    [selection],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (value === null) {
    throw new Error("useAppState must be used inside AppStateProvider");
  }
  return value;
}
