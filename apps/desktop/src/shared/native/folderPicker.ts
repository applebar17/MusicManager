import { invoke } from "@tauri-apps/api/core";

export type FolderPickerResult =
  | { status: "selected"; path: string }
  | { status: "cancelled" }
  | { status: "unavailable"; message: string };

export async function pickMusicFolder(): Promise<FolderPickerResult> {
  try {
    const path = await invoke<string | null>("pick_music_folder");
    if (!path) {
      return { status: "cancelled" };
    }
    return { status: "selected", path };
  } catch {
    return {
      status: "unavailable",
      message:
        "Folder browsing is available in the desktop app. In browser or Docker mode, paste the folder path manually.",
    };
  }
}
