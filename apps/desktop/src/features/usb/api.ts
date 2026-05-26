import { apiGet, apiPost } from "../../shared/api/http";
import type {
  UsbAudioFileMappingCreate,
  UsbFileRead,
  UsbSongCandidateRead,
} from "../../shared/api/types";

export function listUsbFiles(environmentId: string) {
  return apiGet<UsbFileRead[]>(`/environments/${environmentId}/usb/files`);
}

export function listUsbMatchCandidates(
  environmentId: string,
  audioFileId: string,
  query: string,
) {
  const params = new URLSearchParams({ audio_file_id: audioFileId });
  const trimmedQuery = query.trim();
  if (trimmedQuery) {
    params.set("q", trimmedQuery);
  }
  return apiGet<UsbSongCandidateRead[]>(
    `/environments/${environmentId}/usb/match-candidates?${params.toString()}`,
  );
}

export function quarantineUsbAudioFile(environmentId: string, audioFileId: string) {
  return apiPost<UsbFileRead>(
    `/environments/${environmentId}/usb/audio-files/${audioFileId}/quarantine`,
  );
}

export function mapUsbAudioFile(
  environmentId: string,
  audioFileId: string,
  body: UsbAudioFileMappingCreate,
) {
  return apiPost<UsbFileRead, UsbAudioFileMappingCreate>(
    `/environments/${environmentId}/usb/audio-files/${audioFileId}/mapping`,
    body,
  );
}
