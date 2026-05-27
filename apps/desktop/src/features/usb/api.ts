import { apiGet, apiPost, getApiBaseUrl } from "../../shared/api/http";
import type {
  UsbAudioFileMappingCreate,
  UsbFileRead,
  UsbSongCandidateRead,
} from "../../shared/api/types";

type UsbAudioFileBatchQuarantineRequest = {
  audio_file_ids: string[];
  confirmation: string;
};

type UsbAudioFileBatchQuarantineResult = {
  removed: number;
  files: UsbFileRead[];
};

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
export function quarantineUsbAudioFiles(
  environmentId: string,
  data: UsbAudioFileBatchQuarantineRequest,
) {
  return apiPost<UsbAudioFileBatchQuarantineResult, UsbAudioFileBatchQuarantineRequest>(
    `/environments/${environmentId}/usb/audio-files/quarantine`,
    data,
  );
}

export function playbackAudioUrl(environmentId: string, audioFileId: string) {
  const baseUrl = getApiBaseUrl().replace(/\/$/, "");
  return `${baseUrl}/environments/${encodeURIComponent(
    environmentId,
  )}/playback/audio-files/${encodeURIComponent(audioFileId)}`;
}
