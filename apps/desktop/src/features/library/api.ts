import { apiGet, apiPost, apiPut } from "../../shared/api/http";
import type {
  LibraryAlignmentRunRead,
  LibraryConfigure,
  LibraryMetadataAssetRead,
  LibraryMetadataImportRunRead,
  LibraryMetadataIndexEntryRead,
  LibraryRead,
  LibraryTrackRead,
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

export function importLibraryMetadataFromEnvironment(environmentId: string) {
  return apiPost<LibraryMetadataImportRunRead>(
    `/environments/${environmentId}/library/metadata/import`,
  );
}

export function getLatestLibraryMetadataImportRun() {
  return apiGet<LibraryMetadataImportRunRead | null>("/library/metadata/import-runs/latest");
}

export function getLibraryTracks() {
  return apiGet<LibraryTrackRead[]>("/library/tracks");
}

export function getLibraryMetadataAssets() {
  return apiGet<LibraryMetadataAssetRead[]>("/library/metadata/assets");
}

export function getLibraryMetadataIndexEntries() {
  return apiGet<LibraryMetadataIndexEntryRead[]>("/library/metadata/index-entries");
}
