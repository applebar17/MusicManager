import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

type AppSelection = {
  selectedEnvironmentId: string | null;
  selectedPlaylistId: string | null;
};

type AppStateContextValue = AppSelection & {
  selectEnvironment: (environmentId: string | null) => void;
  selectPlaylist: (playlistId: string | null) => void;
};

const AppStateContext = createContext<AppStateContextValue | null>(null);

type AppStateProviderProps = {
  children: ReactNode;
};

export function AppStateProvider({ children }: AppStateProviderProps) {
  const [selection, setSelection] = useState<AppSelection>({
    selectedEnvironmentId: null,
    selectedPlaylistId: null,
  });

  const value = useMemo<AppStateContextValue>(
    () => ({
      ...selection,
      selectEnvironment: (environmentId) => {
        setSelection({
          selectedEnvironmentId: environmentId,
          selectedPlaylistId: null,
        });
      },
      selectPlaylist: (playlistId) => {
        setSelection((current) => ({
          ...current,
          selectedPlaylistId: playlistId,
        }));
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
