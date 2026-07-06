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
  download_path: string | null;
  deprecated_folder_name: string;
  archived_at: string | null;
};

export type EnvironmentCreate = {
  name: string;
  root_path: string;
  download_path?: string | null;
  deprecated_folder_name?: string;
};

export type EnvironmentUpdate = {
  name?: string | null;
  root_path?: string | null;
  download_path?: string | null;
  deprecated_folder_name?: string | null;
};

export type LibraryRead = {
  configured: boolean;
  root_path: string | null;
  created_at: string | null;
  updated_at: string | null;
  track_count: number;
  missing_track_count: number;
  metadata_asset_count: number;
  metadata_index_entry_count: number;
  last_metadata_imported_at: string | null;
};

export type LibraryConfigure = {
  root_path: string;
};

export type LibraryAlignmentItemStatus =
  | "copied"
  | "reused"
  | "updated"
  | "skipped_collision"
  | "skipped_error"
  | "warning_identity_incomplete";

export type LibraryAlignmentRunStatus = "completed" | "completed_with_issues" | "failed";

export type LibraryAlignmentItemRead = {
  id: string;
  status: LibraryAlignmentItemStatus;
  source_path: string;
  target_path: string | null;
  library_track_id: string | null;
  reason_code: string | null;
  reason_message: string | null;
  title: string | null;
  artist: string | null;
  duration_seconds: number | null;
  normalized_title: string | null;
};

export type LibraryAlignmentRunRead = {
  run_id: string;
  library_id: string;
  environment_id: string;
  status: LibraryAlignmentRunStatus;
  started_at: string;
  finished_at: string | null;
  scanned_library_count: number;
  scanned_usb_count: number;
  copied_count: number;
  reused_count: number;
  updated_count: number;
  skipped_collision_count: number;
  skipped_error_count: number;
  warning_count: number;
  items: LibraryAlignmentItemRead[];
  metadata_import: LibraryMetadataImportRunRead | null;
};

export type LibraryMetadataAssetRead = {
  id: string;
  provider: string;
  asset_type: string;
  source_path: string;
  stored_path: string | null;
  status: string;
  error_code: string | null;
  error_message: string | null;
};

export type LibraryMetadataIndexEntryRead = {
  id: string;
  provider: string;
  source_path: string;
  library_track_id: string | null;
  entry_key: string;
  imported_at: string;
};

export type LibraryMetadataImportRunRead = {
  run_id: string;
  library_id: string;
  environment_id: string;
  alignment_run_id: string | null;
  status: "completed" | "completed_with_issues" | "failed";
  started_at: string;
  finished_at: string | null;
  asset_count: number;
  index_entry_count: number;
  error_count: number;
  assets: LibraryMetadataAssetRead[];
  index_entries: LibraryMetadataIndexEntryRead[];
};

export type LibraryTrackRead = {
  id: string;
  filename: string;
  path: string;
  title: string | null;
  artist: string | null;
  duration_seconds: number | null;
  status: "active" | "missing";
  size_bytes: number;
  modified_at: number;
  normalized_title: string | null;
  created_at: string | null;
  updated_at: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  missing_at: string | null;
  mapped_song_count: number;
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
  local_membership_active: boolean;
  added_by_local_audio_file_id: string | null;
  remote_removed_at: string | null;
  match_status: MatchStatus;
  accepted_audio_file_id: string | null;
  accepted_audio_filename?: string | null;
  accepted_audio_relative_path?: string | null;
  accepted_audio_warnings: string[];
  library_match_status: LibraryMatchStatus | null;
  accepted_library_track_id: string | null;
  accepted_library_filename: string | null;
  accepted_library_path: string | null;
  playback_url: string | null;
  source_discovery: SoundCloudTrackDiscoveryRead | null;
};

export type PlaylistDetailRead = {
  id: string;
  environment_id: string;
  name: string;
  remote_playlist_id: string | null;
  active_item_count: number;
  inactive_item_count: number;
  items: PlaylistItemRead[];
  removed_items: PlaylistItemRead[];
};

export type PlaylistLocalItemCreate = {
  audio_file_id: string;
};

export type MatchCandidateRead = {
  audio_file_id: string;
  path: string;
  source_area: "download" | "usb" | "other";
  title: string | null;
  artist: string | null;
  duration_seconds: number | null;
  method: string;
  confidence: number;
  warnings: string[];
};

export type LibraryMatchStatus =
  | "library_matched"
  | "missing_library"
  | "ambiguous_library"
  | "manually_mapped_library";

export type LibraryTrackCandidateRead = {
  library_track_id: string;
  path: string;
  filename: string;
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
  library_status: LibraryMatchStatus | null;
  library_match: LibraryTrackCandidateRead | null;
  library_candidates: LibraryTrackCandidateRead[];
  source_discovery: SoundCloudTrackDiscoveryRead | null;
};

export type LibraryMatchReviewRow = {
  song_id: string;
  title: string;
  artist: string | null;
  duration_seconds: number | null;
  status: LibraryMatchStatus;
  match: LibraryTrackCandidateRead | null;
  candidates: LibraryTrackCandidateRead[];
};

export type MatchingRunSummary = {
  environment_id: string;
  total: number;
  matched: number;
  missing_audio: number;
  ambiguous: number;
  manually_mapped: number;
};

export type LibraryMatchingRunSummary = {
  environment_id: string;
  total: number;
  matched: number;
  missing_library: number;
  ambiguous_library: number;
  manually_mapped_library: number;
};

export type DownloadMatchSummaryRead = {
  checked: number;
  matched: number;
  missing_audio: number;
  ambiguous: number;
  preserved_reviewed: number;
};

export type DownloadMatchRunResultRead = {
  environment_id: string;
  download_path: string;
  scan: ScanSummaryRead;
  matching: DownloadMatchSummaryRead;
};

export type ManualMappingCreate = {
  song_id: string;
  audio_file_id: string;
};

export type ManualLibraryMappingCreate = {
  song_id: string;
  library_track_id: string;
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
  fetched_at: string | null;
};

export type SoundCloudSourceSyncItemRead = {
  song_id: string;
  title: string;
  status: "discovered" | "skipped" | "failed";
  source_url: string | null;
  discovered_url: string | null;
  error_code: string | null;
  error_message: string | null;
};

export type SoundCloudSourceSyncResultRead = {
  environment_id: string;
  total: number;
  discovered: number;
  skipped: number;
  failed: number;
  results: SoundCloudSourceSyncItemRead[];
};

export type ExportPlanCreate = {
  playlist_ids?: string[] | null;
};

export type ExportPlanUpdate = {
  included_item_ids: string[];
  excluded_item_ids: string[];
};

export type ExportAction =
  | "create_folder"
  | "copy_file"
  | "write_tracks_json"
  | "keep_existing"
  | "remove_duplicate_copy"
  | "remove_stale_copy"
  | "preserve_deprecated"
  | "skip";

export type ExportPlanItemRead = {
  export_plan_item_id: string;
  position: number;
  action: ExportAction;
  target_path: string;
  source_path: string | null;
  reason: string | null;
  included: boolean;
  validation_error_code: string | null;
  validation_error_message: string | null;
};

export type ExportPlanValidationErrorRead = {
  export_plan_item_id: string | null;
  code: string;
  message: string;
};

export type ExportPlanRead = {
  export_plan_id: string;
  environment_id: string;
  locked_at: string | null;
  is_valid: boolean;
  validation_error_code: string | null;
  validation_error_message: string | null;
  validation_errors: ExportPlanValidationErrorRead[];
  counts: Record<string, number>;
  items: ExportPlanItemRead[];
};

export type ExportApplyRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "completed_with_failures"
  | "failed";
export type ExportApplyItemStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "skipped";

export type ExportApplyItemResultRead = {
  export_plan_item_id: string | null;
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
