import { apiDelete, apiGet, apiPost } from "../../shared/api/http";
import type {
  AudioFileRead,
  PlaylistDetailRead,
  PlaylistLocalItemCreate,
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

export function listPlaylistLocalFileCandidates(environmentId: string) {
  return apiGet<AudioFileRead[]>(`/environments/${environmentId}/audio-files?status=active`);
}

export function addPlaylistLocalItem(
  environmentId: string,
  playlistId: string,
  data: PlaylistLocalItemCreate,
) {
  return apiPost<PlaylistDetailRead, PlaylistLocalItemCreate>(
    `/environments/${environmentId}/playlists/${playlistId}/local-items`,
    data,
  );
}

export function removePlaylistLocalItem(
  environmentId: string,
  playlistId: string,
  songId: string,
) {
  return apiDelete<PlaylistDetailRead>(
    `/environments/${environmentId}/playlists/${playlistId}/local-items/${songId}`,
  );
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

export function syncSoundCloudPlaylist(environmentId: string, playlistId: string) {
  return apiPost<SoundCloudPlaylistImportResult>(
    `/environments/${environmentId}/soundcloud/playlists/${playlistId}/sync`,
  );
}
