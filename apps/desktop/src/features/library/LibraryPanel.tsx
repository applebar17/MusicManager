import { Database, RefreshCcw, Save, ScanLine, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  LibraryAlignmentRunRead,
  LibraryMetadataImportRunRead,
  LibraryRead,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, ErrorBanner, LoadingState, MetricCard, Panel, PanelHeader } from "../../shared/ui";
import {
  alignLibraryFromEnvironment,
  configureLibrary,
  getLatestLibraryAlignmentRun,
  getLatestLibraryMetadataImportRun,
  getLibrary,
  importLibraryMetadataFromEnvironment,
  scanLibrary,
} from "./api";

type LibraryState =
  | { status: "loading" }
  | { status: "ready"; library: LibraryRead }
  | { status: "error"; message: string };

export function LibraryPanel() {
  const { selectedEnvironmentId } = useAppState();
  const [state, setState] = useState<LibraryState>({ status: "loading" });
  const [latestRun, setLatestRun] = useState<LibraryAlignmentRunRead | null>(null);
  const [latestMetadataRun, setLatestMetadataRun] = useState<LibraryMetadataImportRunRead | null>(
    null,
  );
  const [rootPath, setRootPath] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [isAligning, setIsAligning] = useState(false);
  const [isImportingMetadata, setIsImportingMetadata] = useState(false);

  const loadLibrary = useCallback(() => {
    setState({ status: "loading" });
    setSaveError(null);
    setActionError(null);
    void Promise.all([
      getLibrary(),
      getLatestLibraryAlignmentRun(),
      getLatestLibraryMetadataImportRun(),
    ])
      .then(([library, alignmentRun, metadataRun]) => {
        setRootPath(library.root_path ?? "");
        setLatestRun(alignmentRun);
        setLatestMetadataRun(metadataRun);
        setState({ status: "ready", library });
      })
      .catch((error: unknown) => {
        setState({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "The shared library configuration could not be loaded.",
        });
      });
  }, []);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedPath = rootPath.trim();
    if (!trimmedPath) {
      setSaveError("Choose an existing readable and writable folder.");
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    void configureLibrary({ root_path: trimmedPath })
      .then((library) => {
        setRootPath(library.root_path ?? "");
        setState({ status: "ready", library });
      })
      .catch((error: unknown) => {
        setSaveError(
          error instanceof ApiError
            ? error.message
            : "The shared library path could not be saved.",
        );
      })
      .finally(() => {
        setIsSaving(false);
      });
  };

  const handleScan = () => {
    setIsScanning(true);
    setActionError(null);
    void scanLibrary()
      .then((library) => {
        setState({ status: "ready", library });
      })
      .catch((error: unknown) => {
        setActionError(
          error instanceof ApiError ? error.message : "The shared library scan failed.",
        );
      })
      .finally(() => {
        setIsScanning(false);
      });
  };

  const handleAlign = () => {
    if (!selectedEnvironmentId) {
      setActionError("Select a USB environment before aligning the library.");
      return;
    }
    setIsAligning(true);
    setActionError(null);
    void alignLibraryFromEnvironment(selectedEnvironmentId)
      .then(async (run) => {
        setLatestRun(run);
        setLatestMetadataRun(run.metadata_import);
        setState({ status: "ready", library: await getLibrary() });
      })
      .catch((error: unknown) => {
        setActionError(
          error instanceof ApiError ? error.message : "The USB library alignment failed.",
        );
      })
      .finally(() => {
        setIsAligning(false);
      });
  };

  const handleMetadataImport = () => {
    if (!selectedEnvironmentId) {
      setActionError("Select a USB environment before importing metadata.");
      return;
    }
    setIsImportingMetadata(true);
    setActionError(null);
    void importLibraryMetadataFromEnvironment(selectedEnvironmentId)
      .then(async (run) => {
        setLatestMetadataRun(run);
        setState({ status: "ready", library: await getLibrary() });
      })
      .catch((error: unknown) => {
        setActionError(
          error instanceof ApiError ? error.message : "The metadata import failed.",
        );
      })
      .finally(() => {
        setIsImportingMetadata(false);
      });
  };

  if (state.status === "loading") {
    return <LoadingState label="Loading shared library" />;
  }

  if (state.status === "error") {
    return (
      <ErrorBanner
        title="Library unavailable"
        message={state.message}
        actionLabel="Retry"
        onAction={loadLibrary}
      />
    );
  }

  return (
    <div className="stack">
      <section className="library-header">
        <div>
          <p className="eyebrow">Shared Library</p>
          <h2>Source of truth</h2>
          <p className="muted">
            Configure the global folder that later imports and USB exports will use.
          </p>
        </div>
        <Button
          icon={<RefreshCcw size={16} />}
          onClick={loadLibrary}
          disabled={isSaving}
          aria-label="Refresh library"
        >
          Refresh
        </Button>
      </section>

      <section className="metric-grid">
        <MetricCard
          label="Configuration"
          value={state.library.configured ? "Ready" : "Not set"}
          icon={<Database size={18} />}
          tone={state.library.configured ? "success" : "warning"}
          footer={state.library.configured ? "Library root saved" : "Choose an existing folder"}
        />
        <MetricCard
          label="Library tracks"
          value={formatNumber(state.library.track_count)}
          icon={<Database size={18} />}
          tone="accent"
          footer={`${formatNumber(state.library.missing_track_count)} missing`}
        />
        <MetricCard
          label="Metadata assets"
          value={formatNumber(state.library.metadata_asset_count)}
          icon={<Database size={18} />}
          tone="neutral"
          footer={`${formatNumber(state.library.metadata_index_entry_count)} indexed entries`}
        />
      </section>

      <Panel className="library-actions-panel">
        <PanelHeader eyebrow="Actions" title="Scan and align" icon={<ScanLine size={18} />} />
        <div className="library-action-row">
          <Button
            icon={<ScanLine size={16} />}
            onClick={handleScan}
            disabled={!state.library.configured || isSaving || isScanning || isAligning}
          >
            {isScanning ? "Scanning" : "Scan Library"}
          </Button>
          <Button
            variant="primary"
            icon={<Upload size={16} />}
            onClick={handleAlign}
            disabled={
              !state.library.configured ||
              !selectedEnvironmentId ||
              isSaving ||
              isScanning ||
              isAligning ||
              isImportingMetadata
            }
          >
            {isAligning ? "Aligning" : "Align From Selected USB"}
          </Button>
          <Button
            icon={<Database size={16} />}
            onClick={handleMetadataImport}
            disabled={
              !state.library.configured ||
              !selectedEnvironmentId ||
              isSaving ||
              isScanning ||
              isAligning ||
              isImportingMetadata
            }
          >
            {isImportingMetadata ? "Importing" : "Import Metadata"}
          </Button>
        </div>
        {actionError ? <ErrorBanner title="Library action failed" message={actionError} /> : null}
      </Panel>

      <Panel className="library-config-panel">
        <PanelHeader
          eyebrow="Setup"
          title={state.library.configured ? "Library folder" : "Configure library folder"}
          icon={<Database size={18} />}
        />
        <form className="environment-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Root path</span>
            <input
              value={rootPath}
              onChange={(event) => setRootPath(event.target.value)}
              placeholder="C:\\Music\\Library"
              disabled={isSaving}
            />
          </label>
          {state.library.configured ? (
            <p className="muted">Current library: {state.library.root_path}</p>
          ) : null}
          {saveError ? (
            <ErrorBanner title="Library path rejected" message={saveError} />
          ) : null}
          <div className="form-actions">
            <Button
              type="submit"
              variant="primary"
              icon={<Save size={16} />}
              disabled={isSaving}
            >
              {isSaving ? "Saving" : "Save Library"}
            </Button>
          </div>
        </form>
      </Panel>
      {latestRun ? <LatestAlignmentPanel run={latestRun} /> : null}
      {latestMetadataRun ? <LatestMetadataPanel run={latestMetadataRun} /> : null}
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat().format(value);
}

function LatestAlignmentPanel({ run }: { run: LibraryAlignmentRunRead }) {
  const issueItems = run.items.filter((item) =>
    ["skipped_collision", "skipped_error", "warning_identity_incomplete"].includes(item.status),
  );
  return (
    <Panel className="library-alignment-panel">
      <PanelHeader eyebrow="Latest alignment" title={alignmentTitle(run)} icon={<Upload size={18} />} />
      <div className="library-alignment-summary">
        <span>{formatNumber(run.scanned_usb_count)} USB files scanned</span>
        <span>{formatNumber(run.copied_count)} copied</span>
        <span>{formatNumber(run.reused_count)} reused</span>
        <span>{formatNumber(run.skipped_collision_count)} collisions</span>
        <span>{formatNumber(run.skipped_error_count)} errors</span>
      </div>
      {issueItems.length > 0 ? (
        <div className="library-alignment-issues">
          {issueItems.map((item) => (
            <div className="library-alignment-issue" key={item.id}>
              <strong>{item.title ?? item.source_path}</strong>
              <span>{item.reason_message ?? item.status}</span>
              <small>{item.source_path}</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No alignment issues in the latest run.</p>
      )}
    </Panel>
  );
}

function alignmentTitle(run: LibraryAlignmentRunRead) {
  return run.status === "completed_with_issues" ? "Completed with issues" : "Completed";
}

function LatestMetadataPanel({ run }: { run: LibraryMetadataImportRunRead }) {
  const issueAssets = run.assets.filter((asset) => asset.status !== "copied");
  return (
    <Panel className="library-alignment-panel">
      <PanelHeader
        eyebrow="Latest metadata import"
        title={run.status === "completed_with_issues" ? "Imported with issues" : "Imported"}
        icon={<Database size={18} />}
      />
      <div className="library-alignment-summary">
        <span>{formatNumber(run.asset_count)} assets preserved</span>
        <span>{formatNumber(run.index_entry_count)} index entries</span>
        <span>{formatNumber(run.error_count)} errors</span>
      </div>
      {issueAssets.length > 0 ? (
        <div className="library-alignment-issues">
          {issueAssets.map((asset) => (
            <div className="library-alignment-issue" key={asset.id}>
              <strong>{asset.provider}</strong>
              <span>{asset.error_message ?? asset.status}</span>
              <small>{asset.source_path}</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No metadata import issues in the latest run.</p>
      )}
    </Panel>
  );
}
