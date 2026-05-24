import { apiGet, apiPatch, apiPost } from "../../shared/api/http";
import type {
  AudioFileRead,
  EnvironmentCreate,
  EnvironmentOverviewRead,
  EnvironmentRead,
  EnvironmentUpdate,
  ScanSummaryRead,
} from "../../shared/api/types";

export function listEnvironments(includeArchived = false) {
  const suffix = includeArchived ? "?include_archived=true" : "";
  return apiGet<EnvironmentRead[]>(`/environments${suffix}`);
}

export function createEnvironment(data: EnvironmentCreate) {
  return apiPost<EnvironmentRead, EnvironmentCreate>("/environments", data);
}

export function updateEnvironment(environmentId: string, data: EnvironmentUpdate) {
  return apiPatch<EnvironmentRead, EnvironmentUpdate>(`/environments/${environmentId}`, data);
}

export function archiveEnvironment(environmentId: string) {
  return apiPost<EnvironmentRead>(`/environments/${environmentId}/archive`);
}

export function scanEnvironment(environmentId: string) {
  return apiPost<ScanSummaryRead>(`/environments/${environmentId}/scan`);
}

export function getEnvironmentOverview(environmentId: string) {
  return apiGet<EnvironmentOverviewRead>(`/environments/${environmentId}/overview`);
}

export function listAudioFiles(environmentId: string, status: "active" | "removed" = "active") {
  return apiGet<AudioFileRead[]>(`/environments/${environmentId}/audio-files?status=${status}`);
}

export function listUnmanagedFiles(environmentId: string) {
  return apiGet<AudioFileRead[]>(`/environments/${environmentId}/unmanaged-files`);
}
