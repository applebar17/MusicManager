export type ApiErrorRead = {
  code: string;
  message: string;
};

export type HealthRead = {
  status: "ok";
};

export type EnvironmentRead = {
  id: string;
  name: string;
  root_path: string;
  deprecated_folder_name: string;
  archived_at: string | null;
};

export type EnvironmentCreate = {
  name: string;
  root_path: string;
  deprecated_folder_name?: string;
};

export type EnvironmentUpdate = {
  name?: string | null;
  root_path?: string | null;
  deprecated_folder_name?: string | null;
};

export type ScanSummaryRead = {
  scan_run_id: string;
  environment_id: string;
  added: number;
  changed: number;
  removed: number;
  moved: number;
  unchanged: number;
  total_active: number;
};

export type EnvironmentOverviewRead = {
  environment_id: string;
  playlist_count: number;
  active_playlist_item_count: number;
  inactive_playlist_item_count: number;
  unique_song_count: number;
  active_audio_file_count: number;
  removed_audio_file_count: number;
  unmanaged_audio_file_count: number;
  matched_count: number;
  missing_audio_count: number;
  ambiguous_count: number;
  manually_mapped_count: number;
};

export type AudioFileRead = {
  id: string;
  environment_id: string;
  path: string;
  size_bytes: number;
  modified_at: number;
  status: "active" | "removed";
  title: string | null;
  artist: string | null;
  album: string | null;
  duration_seconds: number | null;
  bpm: number | null;
  key: string | null;
  comment: string | null;
};

export type PlaylistSummaryRead = {
  id: string;
  name: string;
  remote_playlist_id: string | null;
  active_item_count: number;
  inactive_item_count: number;
  matched_count: number;
  missing_audio_count: number;
  ambiguous_count: number;
  manually_mapped_count: number;
};

export type MatchStatus = "matched" | "missing_audio" | "ambiguous" | "manually_mapped";

export type PlaylistItemRead = {
  song_id: string;
  position: number;
  title: string;
  artist: string | null;
  duration_seconds: number | null;
  remote_membership_active: boolean;
  match_status: MatchStatus;
  accepted_audio_file_id: string | null;
  accepted_audio_filename?: string | null;
  accepted_audio_relative_path?: string | null;
  accepted_audio_warnings: string[];
  playback_url: string | null;
};

export type PlaylistDetailRead = {
  id: string;
  environment_id: string;
  name: string;
  remote_playlist_id: string | null;
  active_item_count: number;
  inactive_item_count: number;
  items: PlaylistItemRead[];
};

export type MatchCandidateRead = {
  audio_file_id: string;
  path: string;
  title: string | null;
  artist: string | null;
  duration_seconds: number | null;
  method: string;
  confidence: number;
  warnings: string[];
};

export type MatchReviewRow = {
  song_id: string;
  title: string;
  artist: string | null;
  duration_seconds: number | null;
  status: MatchStatus;
  match: MatchCandidateRead | null;
  candidates: MatchCandidateRead[];
};

export type MatchingRunSummary = {
  environment_id: string;
  total: number;
  matched: number;
  missing_audio: number;
  ambiguous: number;
  manually_mapped: number;
};

export type ManualMappingCreate = {
  song_id: string;
  audio_file_id: string;
};

export type UsbMatchedSongRead = {
  song_id: string;
  title: string;
  artist: string | null;
  duration_seconds: number | null;
  playlists: string[];
  method: string;
  confidence: number;
  reviewed: boolean;
  local_copy_count: number;
  local_audio_file_ids: string[];
};

export type UsbFileRead = {
  audio_file_id: string;
  environment_id: string;
  path: string;
  relative_path: string;
  folder_parts: string[];
  filename: string;
  audio_status: "active" | "removed";
  match_status: "matched" | "unmatched";
  warnings: string[];
  title: string | null;
  artist: string | null;
  album: string | null;
  duration_seconds: number | null;
  bpm: number | null;
  key: string | null;
  comment: string | null;
  size_bytes: number;
  modified_at: number;
  matched_song: UsbMatchedSongRead | null;
};

export type UsbSongCandidateRead = {
  song_id: string;
  title: string;
  artist: string | null;
  duration_seconds: number | null;
  playlists: string[];
  status: MatchStatus;
  method: string | null;
  confidence: number;
};

export type UsbAudioFileMappingCreate = {
  song_id: string;
};

export type SoundCloudPlaylistImportRequest = {
  url: string;
};

export type SoundCloudPlaylistImportResult = {
  environment_id: string;
  remote_playlist_id: string;
  playlist_id: string;
  sync_snapshot_id: string;
  playlist_name: string;
  track_count: number;
  added: number;
  removed: number;
  reactivated: number;
  reordered: number;
  metadata_changed: number;
  unchanged: number;
  warnings: string[];
};

export type SoundCloudPlaylistSyncItemResult = {
  playlist_id: string;
  remote_playlist_id: string;
  source_url: string;
  status: "synced" | "failed";
  playlist_name: string | null;
  track_count: number | null;
  added: number | null;
  removed: number | null;
  reactivated: number | null;
  reordered: number | null;
  metadata_changed: number | null;
  unchanged: number | null;
  warnings: string[];
  error_code: string | null;
  error_message: string | null;
};

export type SoundCloudPlaylistSyncAllResult = {
  environment_id: string;
  total: number;
  succeeded: number;
  failed: number;
  results: SoundCloudPlaylistSyncItemResult[];
};

export type SoundCloudDiscoveryLinkRead = {
  url: string;
  label: string | null;
  kind: string;
  source: string;
};

export type SoundCloudTrackDiscoveryRead = {
  environment_id: string;
  song_id: string;
  track_url: string;
  track_urn: string | null;
  title: string;
  artist: string | null;
  description: string | null;
  purchase_title: string | null;
  purchase_url: string | null;
  downloadable: boolean | null;
  download_url: string | null;
  links: SoundCloudDiscoveryLinkRead[];
  tags: string[];
  release_metadata: Record<string, string>;
  warnings: string[];
};

export type ExportPlanCreate = {
  playlist_ids?: string[] | null;
};

export type ExportAction =
  | "create_folder"
  | "copy_file"
  | "keep_existing"
  | "remove_duplicate_copy"
  | "remove_stale_copy"
  | "preserve_deprecated"
  | "skip";

export type ExportPlanItemRead = {
  action: ExportAction;
  target_path: string;
  source_path: string | null;
  reason: string | null;
};

export type ExportPlanRead = {
  export_plan_id: string;
  environment_id: string;
  counts: Record<string, number>;
  items: ExportPlanItemRead[];
};

export type ExportApplyRunStatus = "completed" | "completed_with_failures" | "failed";
export type ExportApplyItemStatus = "succeeded" | "failed" | "skipped";

export type ExportApplyItemResultRead = {
  action: ExportAction;
  target_path: string;
  status: ExportApplyItemStatus;
  source_path: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string | null;
};

export type ExportApplyRunRead = {
  apply_run_id: string;
  export_plan_id: string;
  environment_id: string;
  status: ExportApplyRunStatus;
  counts: Record<string, number>;
  item_results: ExportApplyItemResultRead[];
};
