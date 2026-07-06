import { apiGet, apiPost } from "../../shared/api/http";
import type {
  ManualLibraryMappingCreate,
  LibraryMatchingRunSummary,
  LibraryTrackCandidateRead,
  MatchReviewRow,
  SoundCloudTrackDiscoveryRead,
  SoundCloudSourceSyncResultRead,
} from "../../shared/api/types";

export function runLibraryMatching(environmentId: string) {
  return apiPost<LibraryMatchingRunSummary>(
    `/environments/${environmentId}/library/matching/run`,
  );
}

export function listMatchReview(environmentId: string) {
  return apiGet<MatchReviewRow[]>(`/environments/${environmentId}/matching/review`);
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

export function createManualLibraryMapping(
  environmentId: string,
  data: ManualLibraryMappingCreate,
) {
  return apiPost<unknown, ManualLibraryMappingCreate>(
    `/environments/${environmentId}/library/matching/manual-mappings`,
    data,
  );
}
