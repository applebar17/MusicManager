import { Database, RefreshCcw, Save } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../../shared/api/http";
import type { LibraryRead } from "../../shared/api/types";
import { Button, ErrorBanner, LoadingState, MetricCard, Panel, PanelHeader } from "../../shared/ui";
import { configureLibrary, getLibrary } from "./api";

type LibraryState =
  | { status: "loading" }
  | { status: "ready"; library: LibraryRead }
  | { status: "error"; message: string };

export function LibraryPanel() {
  const [state, setState] = useState<LibraryState>({ status: "loading" });
  const [rootPath, setRootPath] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const loadLibrary = useCallback(() => {
    setState({ status: "loading" });
    setSaveError(null);
    void getLibrary()
      .then((library) => {
        setRootPath(library.root_path ?? "");
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
          footer="Scanning starts in a later wave"
        />
      </section>

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
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat().format(value);
}
