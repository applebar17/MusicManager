import { apiGet, apiPost } from "../../shared/api/http";
import type {
  PlaylistDetailRead,
  PlaylistSummaryRead,
  SoundCloudPlaylistSyncAllResult,
  SoundCloudPlaylistImportRequest,
  SoundCloudPlaylistImportResult,
} from "../../shared/api/types";

export function listPlaylists(environmentId: string) {
  return apiGet<PlaylistSummaryRead[]>(`/environments/${environmentId}/playlists`);
}

export function getPlaylistDetail(environmentId: string, playlistId: string) {
  return apiGet<PlaylistDetailRead>(`/environments/${environmentId}/playlists/${playlistId}`);
}

export function importSoundCloudPlaylist(environmentId: string, url: string) {
  return apiPost<SoundCloudPlaylistImportResult, SoundCloudPlaylistImportRequest>(
    `/environments/${environmentId}/soundcloud/playlists`,
    { url },
  );
}

export function syncAllSoundCloudPlaylists(environmentId: string) {
  return apiPost<SoundCloudPlaylistSyncAllResult>(
    `/environments/${environmentId}/soundcloud/playlists/sync-all`,
  );
}
