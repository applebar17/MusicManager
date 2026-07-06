import { apiGet, apiPost, apiPut } from "../../shared/api/http";
import type {
  LibraryAlignmentRunRead,
  LibraryConfigure,
  LibraryRead,
} from "../../shared/api/types";

export function getLibrary() {
  return apiGet<LibraryRead>("/library");
}

export function configureLibrary(data: LibraryConfigure) {
  return apiPut<LibraryRead, LibraryConfigure>("/library", data);
}

export function scanLibrary() {
  return apiPost<LibraryRead>("/library/scan");
}

export function alignLibraryFromEnvironment(environmentId: string) {
  return apiPost<LibraryAlignmentRunRead>(`/environments/${environmentId}/library/align`);
}

export function getLatestLibraryAlignmentRun() {
  return apiGet<LibraryAlignmentRunRead | null>("/library/alignment-runs/latest");
}
