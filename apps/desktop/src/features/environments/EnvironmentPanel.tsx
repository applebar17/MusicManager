import {
  AudioLines,
  CheckCircle2,
  FolderOpen,
  HardDrive,
  Library,
  ListMusic,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  AudioFileRead,
  EnvironmentOverviewRead,
  EnvironmentRead,
  ScanSummaryRead,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import {
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorBanner,
  LoadingState,
  MetricCard,
  Panel,
  PanelHeader,
  PathDisplay,
  StatusBadge,
} from "../../shared/ui";
import {
  archiveEnvironment,
  createEnvironment,
  getEnvironmentOverview,
  listAudioFiles,
  listEnvironments,
  listUnmanagedFiles,
  scanEnvironment,
  updateEnvironment,
} from "./api";

type DashboardData = {
  overview: EnvironmentOverviewRead;
  activeAudioFiles: AudioFileRead[];
  removedAudioFiles: AudioFileRead[];
  unmanagedAudioFiles: AudioFileRead[];
};

type EnvironmentFormState = {
  name: string;
  rootPath: string;
  deprecatedFolderName: string;
};

type ActivityItem = {
  id: string;
  title: string;
  detail: string;
  tone: "accent" | "success" | "warning" | "danger";
};

const emptyForm: EnvironmentFormState = {
  name: "",
  rootPath: "",
  deprecatedFolderName: "_deprecated",
};

export function EnvironmentPanel() {
  const { selectedEnvironmentId, selectEnvironment } = useAppState();
  const [environments, setEnvironments] = useState<EnvironmentRead[]>([]);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [lastScan, setLastScan] = useState<ScanSummaryRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshingDashboard, setIsRefreshingDashboard] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<EnvironmentFormState>(emptyForm);
  const [editForm, setEditForm] = useState<EnvironmentFormState>(emptyForm);
  const [archiveConfirmOpen, setArchiveConfirmOpen] = useState(false);

  const selectedEnvironment = useMemo(
    () => environments.find((environment) => environment.id === selectedEnvironmentId) ?? null,
    [environments, selectedEnvironmentId],
  );

  const loadEnvironments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const items = await listEnvironments();
      setEnvironments(items);
      if (!selectedEnvironmentId || !items.some((item) => item.id === selectedEnvironmentId)) {
        selectEnvironment(items[0]?.id ?? null);
      }
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }, [selectEnvironment, selectedEnvironmentId]);

  const refreshDashboard = useCallback(
    async (environmentId: string) => {
      setIsRefreshingDashboard(true);
      setError(null);
      try {
        const [overview, activeAudioFiles, removedAudioFiles, unmanagedAudioFiles] =
          await Promise.all([
            getEnvironmentOverview(environmentId),
            listAudioFiles(environmentId, "active"),
            listAudioFiles(environmentId, "removed"),
            listUnmanagedFiles(environmentId),
          ]);
        setDashboardData({
          overview,
          activeAudioFiles,
          removedAudioFiles,
          unmanagedAudioFiles,
        });
      } catch (loadError) {
        setDashboardData(null);
        setError(errorMessage(loadError));
      } finally {
        setIsRefreshingDashboard(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadEnvironments();
  }, [loadEnvironments]);

  useEffect(() => {
    if (!selectedEnvironmentId) {
      setDashboardData(null);
      return;
    }
    void refreshDashboard(selectedEnvironmentId);
  }, [refreshDashboard, selectedEnvironmentId]);

  useEffect(() => {
    if (!selectedEnvironment) {
      setEditForm(emptyForm);
      return;
    }
    setEditForm({
      name: selectedEnvironment.name,
      rootPath: selectedEnvironment.root_path,
      deprecatedFolderName: selectedEnvironment.deprecated_folder_name,
    });
  }, [selectedEnvironment]);

  async function handleCreateEnvironment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const created = await createEnvironment({
        name: createForm.name.trim(),
        root_path: createForm.rootPath.trim(),
        deprecated_folder_name: createForm.deprecatedFolderName.trim() || "_deprecated",
      });
      setCreateForm(emptyForm);
      setEnvironments((current) => [...current, created]);
      selectEnvironment(created.id);
    } catch (createError) {
      setError(errorMessage(createError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleUpdateEnvironment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEnvironment) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await updateEnvironment(selectedEnvironment.id, {
        name: editForm.name.trim(),
        root_path: editForm.rootPath.trim(),
        deprecated_folder_name: editForm.deprecatedFolderName.trim() || "_deprecated",
      });
      setEnvironments((current) =>
        current.map((environment) => (environment.id === updated.id ? updated : environment)),
      );
      await refreshDashboard(updated.id);
    } catch (updateError) {
      setError(errorMessage(updateError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleArchiveEnvironment() {
    if (!selectedEnvironment) {
      return;
    }
    setArchiveConfirmOpen(false);
    setIsSubmitting(true);
    setError(null);
    try {
      await archiveEnvironment(selectedEnvironment.id);
      const remaining = environments.filter((environment) => environment.id !== selectedEnvironment.id);
      setEnvironments(remaining);
      selectEnvironment(remaining[0]?.id ?? null);
      setDashboardData(null);
      setLastScan(null);
    } catch (archiveError) {
      setError(errorMessage(archiveError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleScanEnvironment() {
    if (!selectedEnvironment) {
      return;
    }
    setIsScanning(true);
    setError(null);
    try {
      const scan = await scanEnvironment(selectedEnvironment.id);
      setLastScan(scan);
      await refreshDashboard(selectedEnvironment.id);
    } catch (scanError) {
      setError(errorMessage(scanError));
    } finally {
      setIsScanning(false);
    }
  }

  const activityItems = useMemo(() => scanActivity(lastScan), [lastScan]);
  const matchPercentage = dashboardData ? calculateMatchPercentage(dashboardData.overview) : 0;

  return (
    <div className="environment-dashboard">
      <TopActionBar
        environments={environments}
        selectedEnvironmentId={selectedEnvironmentId}
        isScanning={isScanning}
        onSelectEnvironment={selectEnvironment}
        onScan={handleScanEnvironment}
      />

      {error ? (
        <ErrorBanner
          title="Environment dashboard error"
          message={error}
          actionLabel="Retry"
          onAction={() => {
            void loadEnvironments();
            if (selectedEnvironmentId) {
              void refreshDashboard(selectedEnvironmentId);
            }
          }}
        />
      ) : null}

      {isLoading ? <LoadingState label="Loading environments" /> : null}

      {!isLoading && environments.length === 0 ? (
        <CreateEnvironmentPanel
          form={createForm}
          isSubmitting={isSubmitting}
          onSubmit={handleCreateEnvironment}
          onChange={setCreateForm}
        />
      ) : null}

      {selectedEnvironment ? (
        <>
          <section className="environment-hero">
            <div>
              <h2>Environment Overview</h2>
              <PathDisplay path={selectedEnvironment.root_path} />
            </div>
            <div className="scan-summary-card">
              <div>
                <span className="muted">Last scan</span>
                <strong>{lastScan ? "Current session" : "Not scanned this session"}</strong>
              </div>
              <Button
                disabled={isScanning}
                icon={<RefreshCw size={16} />}
                onClick={handleScanEnvironment}
              >
                {isScanning ? "Scanning" : "Scan Environment"}
              </Button>
            </div>
          </section>

          {isRefreshingDashboard && !dashboardData ? (
            <LoadingState label="Loading dashboard metrics" />
          ) : null}

          {dashboardData ? (
            <>
              <section className="metric-grid">
                <MetricCard
                  icon={<ListMusic size={18} />}
                  label="Playlists"
                  value={formatNumber(dashboardData.overview.playlist_count)}
                />
                <MetricCard
                  icon={<Library size={18} />}
                  label="Unique Songs"
                  value={formatNumber(dashboardData.overview.unique_song_count)}
                />
                <MetricCard
                  icon={<AudioLines size={18} />}
                  label="Active Audio Files"
                  value={formatNumber(dashboardData.overview.active_audio_file_count)}
                />
                <MetricCard
                  icon={<ShieldCheck size={18} />}
                  label="Match Status"
                  tone={matchPercentage >= 80 ? "success" : matchPercentage > 0 ? "warning" : "danger"}
                  value={`${matchPercentage}% Matched`}
                  footer={
                    <div className="metric-dot-row">
                      <MetricDot tone="success" value={dashboardData.overview.matched_count} />
                      <MetricDot tone="danger" value={dashboardData.overview.missing_audio_count} />
                      <MetricDot tone="warning" value={dashboardData.overview.ambiguous_count} />
                      <MetricDot tone="accent" value={dashboardData.overview.manually_mapped_count} />
                    </div>
                  }
                />
              </section>

              <section className="dashboard-grid">
                <Panel className="activity-panel">
                  <PanelHeader eyebrow="Recent" title="Environment Activity" />
                  {activityItems.length > 0 ? (
                    <div className="activity-list">
                      {activityItems.map((item) => (
                        <ActivityRow item={item} key={item.id} />
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      title="No session activity yet"
                      description="Scan the selected environment to populate recent activity from real backend results."
                    />
                  )}
                </Panel>

                <Panel className="system-panel">
                  <PanelHeader eyebrow="System" title="Status" />
                  <div className="system-stack">
                    <SystemStatusRow label="Root path" value="Configured" tone="success" />
                    <SystemStatusRow
                      label="Active files"
                      value={formatNumber(dashboardData.activeAudioFiles.length)}
                      tone="success"
                    />
                    <SystemStatusRow
                      label="Removed files"
                      value={formatNumber(dashboardData.removedAudioFiles.length)}
                      tone={dashboardData.removedAudioFiles.length ? "warning" : "neutral"}
                    />
                    <SystemStatusRow
                      label="Unmanaged files"
                      value={formatNumber(dashboardData.unmanagedAudioFiles.length)}
                      tone={dashboardData.unmanagedAudioFiles.length ? "warning" : "neutral"}
                    />
                  </div>
                  <EnvironmentEditForm
                    form={editForm}
                    isSubmitting={isSubmitting}
                    onArchive={() => setArchiveConfirmOpen(true)}
                    onChange={setEditForm}
                    onSubmit={handleUpdateEnvironment}
                  />
                </Panel>
              </section>
            </>
          ) : null}
        </>
      ) : null}

      <ConfirmDialog
        confirmLabel="Archive"
        message="Archived environments are hidden from the dashboard but their backend data is preserved."
        open={archiveConfirmOpen}
        title="Archive this environment?"
        onCancel={() => setArchiveConfirmOpen(false)}
        onConfirm={handleArchiveEnvironment}
      />
    </div>
  );
}

type TopActionBarProps = {
  environments: EnvironmentRead[];
  selectedEnvironmentId: string | null;
  isScanning: boolean;
  onSelectEnvironment: (environmentId: string | null) => void;
  onScan: () => void;
};

function TopActionBar({
  environments,
  selectedEnvironmentId,
  isScanning,
  onSelectEnvironment,
  onScan,
}: TopActionBarProps) {
  const selectedEnvironmentName =
    environments.find((environment) => environment.id === selectedEnvironmentId)?.name ??
    "No environment selected";

  return (
    <header className="top-action-bar">
      <div className="top-tabs" aria-label="Environment stage">
        <span>Environment</span>
        <span className="top-tabs__active">{selectedEnvironmentName}</span>
      </div>
      <div className="top-actions">
        <EnvironmentSelect
          environments={environments}
          selectedEnvironmentId={selectedEnvironmentId}
          onSelectEnvironment={onSelectEnvironment}
        />
        <button className="icon-button" disabled type="button" title="Folder picker arrives in a later wave">
          <FolderOpen size={17} />
        </button>
        <button
          className="icon-button"
          disabled={isScanning || !selectedEnvironmentId}
          type="button"
          title="Scan"
          onClick={onScan}
        >
          <RefreshCw size={17} />
        </button>
        <Button disabled={!selectedEnvironmentId || isScanning} variant="primary" onClick={onScan}>
          {isScanning ? "Scanning" : "Scan"}
        </Button>
      </div>
    </header>
  );
}

type EnvironmentSelectProps = {
  environments: EnvironmentRead[];
  selectedEnvironmentId: string | null;
  onSelectEnvironment: (environmentId: string | null) => void;
};

function EnvironmentSelect({
  environments,
  selectedEnvironmentId,
  onSelectEnvironment,
}: EnvironmentSelectProps) {
  return (
    <label className="environment-select">
      <HardDrive size={16} />
      <select
        value={selectedEnvironmentId ?? ""}
        onChange={(event) => onSelectEnvironment(event.target.value || null)}
      >
        {environments.length === 0 ? <option value="">No environment</option> : null}
        {environments.map((environment) => (
          <option value={environment.id} key={environment.id}>
            {environment.name}
          </option>
        ))}
      </select>
    </label>
  );
}

type EnvironmentFormProps = {
  form: EnvironmentFormState;
  isSubmitting: boolean;
  onChange: (form: EnvironmentFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function CreateEnvironmentPanel({
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: EnvironmentFormProps) {
  return (
    <Panel className="environment-form-panel">
      <PanelHeader eyebrow="Create" title="Connect a music environment" icon={<HardDrive size={18} />} />
      <p className="muted">
        Enter an existing folder path. The backend validates that it exists and is readable.
      </p>
      <EnvironmentForm
        buttonLabel={isSubmitting ? "Creating" : "Create Environment"}
        form={form}
        isSubmitting={isSubmitting}
        onChange={onChange}
        onSubmit={onSubmit}
      />
    </Panel>
  );
}

type EnvironmentEditFormProps = EnvironmentFormProps & {
  onArchive: () => void;
};

function EnvironmentEditForm({
  form,
  isSubmitting,
  onArchive,
  onChange,
  onSubmit,
}: EnvironmentEditFormProps) {
  return (
    <form className="environment-form compact" onSubmit={onSubmit}>
      <Field
        label="Name"
        value={form.name}
        onChange={(value) => onChange({ ...form, name: value })}
      />
      <Field
        label="Root path"
        value={form.rootPath}
        onChange={(value) => onChange({ ...form, rootPath: value })}
      />
      <Field
        label="Deprecated folder"
        value={form.deprecatedFolderName}
        onChange={(value) => onChange({ ...form, deprecatedFolderName: value })}
      />
      <div className="form-actions split">
        <Button disabled={isSubmitting} type="submit">
          Save Changes
        </Button>
        <Button disabled={isSubmitting} variant="danger" onClick={onArchive}>
          Archive
        </Button>
      </div>
    </form>
  );
}

type EnvironmentFormFieldsProps = EnvironmentFormProps & {
  buttonLabel: string;
};

function EnvironmentForm({
  buttonLabel,
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: EnvironmentFormFieldsProps) {
  return (
    <form className="environment-form" onSubmit={onSubmit}>
      <Field
        label="Name"
        placeholder="Main USB - Summer Tour"
        required
        value={form.name}
        onChange={(value) => onChange({ ...form, name: value })}
      />
      <Field
        label="Root path"
        placeholder="/Volumes/DJ_DRIVE/Music"
        required
        value={form.rootPath}
        onChange={(value) => onChange({ ...form, rootPath: value })}
      />
      <Field
        label="Deprecated folder"
        value={form.deprecatedFolderName}
        onChange={(value) => onChange({ ...form, deprecatedFolderName: value })}
      />
      <div className="form-actions">
        <Button disabled={isSubmitting} type="submit" variant="primary">
          {buttonLabel}
        </Button>
      </div>
    </form>
  );
}

type FieldProps = {
  label: string;
  value: string;
  placeholder?: string;
  required?: boolean;
  onChange: (value: string) => void;
};

function Field({ label, value, placeholder, required = false, onChange }: FieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        placeholder={placeholder}
        required={required}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

type MetricDotProps = {
  tone: "accent" | "success" | "warning" | "danger";
  value: number;
};

function MetricDot({ tone, value }: MetricDotProps) {
  return (
    <span className="metric-dot-item">
      <span className={`metric-dot metric-dot--${tone}`} />
      {formatNumber(value)}
    </span>
  );
}

type ActivityRowProps = {
  item: ActivityItem;
};

function ActivityRow({ item }: ActivityRowProps) {
  const icon =
    item.tone === "danger" ? (
      <TriangleAlert size={18} />
    ) : item.tone === "success" ? (
      <CheckCircle2 size={18} />
    ) : item.tone === "warning" ? (
      <TriangleAlert size={18} />
    ) : (
      <RefreshCw size={18} />
    );
  return (
    <div className="activity-row">
      <span className={`activity-icon activity-icon--${item.tone}`}>{icon}</span>
      <div>
        <strong>{item.title}</strong>
        <span>{item.detail}</span>
      </div>
      <span className="activity-time">Now</span>
    </div>
  );
}

type SystemStatusRowProps = {
  label: string;
  value: string;
  tone: "neutral" | "success" | "warning";
};

function SystemStatusRow({ label, value, tone }: SystemStatusRowProps) {
  return (
    <div className="system-status-row">
      <span>{label}</span>
      <StatusBadge tone={tone === "success" ? "success" : tone === "warning" ? "warning" : "neutral"}>
        {value}
      </StatusBadge>
    </div>
  );
}

function scanActivity(scan: ScanSummaryRead | null): ActivityItem[] {
  if (!scan) {
    return [];
  }

  const items: ActivityItem[] = [];
  if (scan.added > 0) {
    items.push({
      id: "added",
      title: `${formatNumber(scan.added)} new audio files found`,
      detail: `Scan ${scan.scan_run_id}`,
      tone: "accent",
    });
  }
  if (scan.changed > 0 || scan.moved > 0) {
    items.push({
      id: "changed",
      title: `${formatNumber(scan.changed + scan.moved)} files changed or moved`,
      detail: `${formatNumber(scan.changed)} changed, ${formatNumber(scan.moved)} moved`,
      tone: "warning",
    });
  }
  if (scan.removed > 0) {
    items.push({
      id: "removed",
      title: `${formatNumber(scan.removed)} files no longer present`,
      detail: "They remain tracked as removed audio files.",
      tone: "danger",
    });
  }
  if (scan.unchanged > 0) {
    items.push({
      id: "unchanged",
      title: `${formatNumber(scan.unchanged)} files unchanged`,
      detail: `${formatNumber(scan.total_active)} active files after scan`,
      tone: "success",
    });
  }
  if (items.length === 0) {
    items.push({
      id: "empty",
      title: "Scan completed with no file changes",
      detail: `${formatNumber(scan.total_active)} active files remain tracked`,
      tone: "success",
    });
  }
  return items;
}

function calculateMatchPercentage(overview: EnvironmentOverviewRead) {
  const total =
    overview.matched_count +
    overview.missing_audio_count +
    overview.ambiguous_count +
    overview.manually_mapped_count;
  if (total === 0) {
    return 0;
  }
  return Math.round(((overview.matched_count + overview.manually_mapped_count) / total) * 100);
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong while talking to the backend.";
}

function formatNumber(value: number) {
  return new Intl.NumberFormat().format(value);
}
