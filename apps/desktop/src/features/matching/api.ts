import { apiGet, apiPost, getApiBaseUrl } from "../../shared/api/http";
import type {
  ManualMappingCreate,
  MatchingRunSummary,
  MatchReviewRow,
} from "../../shared/api/types";

export function runMatching(environmentId: string) {
  return apiPost<MatchingRunSummary>(`/environments/${environmentId}/matching/run`);
}

export function listMatchReview(environmentId: string) {
  return apiGet<MatchReviewRow[]>(`/environments/${environmentId}/matching/review`);
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

export function playbackAudioUrl(environmentId: string, audioFileId: string) {
  const baseUrl = getApiBaseUrl().replace(/\/$/, "");
  return `${baseUrl}/environments/${encodeURIComponent(
    environmentId,
  )}/playback/audio-files/${encodeURIComponent(audioFileId)}`;
}
