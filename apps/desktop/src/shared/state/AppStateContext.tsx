import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type AppView = "dashboard" | "playlists" | "matching" | "export" | "settings";

type AppSelection = {
  activeView: AppView;
  selectedEnvironmentId: string | null;
  selectedPlaylistId: string | null;
};

type AppStateContextValue = AppSelection & {
  selectView: (view: AppView) => void;
  selectEnvironment: (environmentId: string | null) => void;
  selectPlaylist: (playlistId: string | null) => void;
};

const AppStateContext = createContext<AppStateContextValue | null>(null);

type AppStateProviderProps = {
  children: ReactNode;
};

export function AppStateProvider({ children }: AppStateProviderProps) {
  const [selection, setSelection] = useState<AppSelection>({
    activeView: "dashboard",
    selectedEnvironmentId: null,
    selectedPlaylistId: null,
  });

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
