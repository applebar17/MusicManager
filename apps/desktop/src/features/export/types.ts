export type ExportAction =
  | "create_folder"
  | "copy_file"
  | "remove_stale_copy"
  | "preserve_deprecated"
  | "skip";

export type ExportPlanItem = {
  action: ExportAction;
  sourcePath?: string;
  targetPath: string;
  reason?: string;
};

