import { apiGet, apiPost, getApiBaseUrl } from "../../shared/api/http";
import type {
  ManualMappingCreate,
  ManualLibraryMappingCreate,
  DownloadMatchRunResultRead,
  LibraryMatchingRunSummary,
  LibraryTrackCandidateRead,
  MatchCandidateRead,
  MatchingRunSummary,
  MatchReviewRow,
  SoundCloudTrackDiscoveryRead,
  SoundCloudSourceSyncResultRead,
} from "../../shared/api/types";

export function runMatching(environmentId: string) {
  return apiPost<MatchingRunSummary>(`/environments/${environmentId}/matching/run`);
}

export function runLibraryMatching(environmentId: string) {
  return apiPost<LibraryMatchingRunSummary>(
    `/environments/${environmentId}/library/matching/run`,
  );
}

export function matchDownloads(environmentId: string) {
  return apiPost<DownloadMatchRunResultRead>(
    `/environments/${environmentId}/matching/downloads/run`,
  );
}

export function listMatchReview(environmentId: string) {
  return apiGet<MatchReviewRow[]>(`/environments/${environmentId}/matching/review`);
}

export function listManualFileCandidates(
  environmentId: string,
  songId: string,
  query: string,
) {
  const params = new URLSearchParams({ song_id: songId });
  if (query.trim()) {
    params.set("q", query.trim());
  }
  return apiGet<MatchCandidateRead[]>(
    `/environments/${environmentId}/matching/manual-file-candidates?${params.toString()}`,
  );
}

export function listManualLibraryTrackCandidates(
  environmentId: string,
  songId: string,
  query: string,
) {
  const params = new URLSearchParams({ song_id: songId });
  if (query.trim()) {
    params.set("q", query.trim());
  }
  return apiGet<LibraryTrackCandidateRead[]>(
    `/environments/${environmentId}/library/matching/manual-track-candidates?${params.toString()}`,
  );
}

export function discoverSoundCloudTrack(environmentId: string, songId: string) {
  return apiGet<SoundCloudTrackDiscoveryRead>(
    `/environments/${environmentId}/songs/${songId}/soundcloud-discovery`,
  );
}

export function syncMissingSoundCloudSources(environmentId: string) {
  return apiPost<SoundCloudSourceSyncResultRead>(
    `/environments/${environmentId}/soundcloud-discovery/sync-missing`,
  );
}

export function createManualMapping(
  environmentId: string,
  data: ManualMappingCreate,
) {
  return apiPost<MatchReviewRow, ManualMappingCreate>(
    `/environments/${environmentId}/matching/manual-mappings`,
    data,
  );
}

export function createManualLibraryMapping(
  environmentId: string,
  data: ManualLibraryMappingCreate,
) {
  return apiPost<unknown, ManualLibraryMappingCreate>(
    `/environments/${environmentId}/library/matching/manual-mappings`,
    data,
  );
}

export function playbackAudioUrl(environmentId: string, audioFileId: string) {
  const baseUrl = getApiBaseUrl().replace(/\/$/, "");
  return `${baseUrl}/environments/${encodeURIComponent(
    environmentId,
  )}/playback/audio-files/${encodeURIComponent(audioFileId)}`;
}
