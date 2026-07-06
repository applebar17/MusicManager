import { apiGet, apiPut } from "../../shared/api/http";
import type { LibraryConfigure, LibraryRead } from "../../shared/api/types";

export function getLibrary() {
  return apiGet<LibraryRead>("/library");
}

export function configureLibrary(data: LibraryConfigure) {
  return apiPut<LibraryRead, LibraryConfigure>("/library", data);
}
