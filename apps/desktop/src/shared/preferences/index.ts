export type AppPreferences = {
  selectedEnvironmentId: string | null;
  selectedPlaylistId: string | null;
  selectedExportPlanId: string | null;
  selectedExportApplyRunId: string | null;
};

const STORAGE_KEY = "music-manager.preferences.v1";

const emptyPreferences: AppPreferences = {
  selectedEnvironmentId: null,
  selectedPlaylistId: null,
  selectedExportPlanId: null,
  selectedExportApplyRunId: null,
};

export function loadPreferences(): AppPreferences {
  if (!storageAvailable()) {
    return emptyPreferences;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return emptyPreferences;
    }
    const data = JSON.parse(raw) as Partial<AppPreferences>;
    return {
      selectedEnvironmentId: stringOrNull(data.selectedEnvironmentId),
      selectedPlaylistId: stringOrNull(data.selectedPlaylistId),
      selectedExportPlanId: stringOrNull(data.selectedExportPlanId),
      selectedExportApplyRunId: stringOrNull(data.selectedExportApplyRunId),
    };
  } catch {
    return emptyPreferences;
  }
}

export function savePreferences(preferences: AppPreferences) {
  if (!storageAvailable()) {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
}

function storageAvailable() {
  return typeof window !== "undefined" && "localStorage" in window;
}

function stringOrNull(value: unknown) {
  return typeof value === "string" && value.length > 0 ? value : null;
}
