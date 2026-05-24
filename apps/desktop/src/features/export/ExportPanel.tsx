import {
  Archive,
  ArrowRight,
  Ban,
  Copy,
  Filter,
  FolderPlus,
  ListChecks,
  Loader2,
  Lock,
  RefreshCw,
  Rocket,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  ExportAction,
  ExportPlanItemRead,
  ExportPlanRead,
  PlaylistSummaryRead,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, EmptyState, ErrorBanner, LoadingState, Panel } from "../../shared/ui";
import { listPlaylists } from "../playlists/api";
import { createExportPlan, getExportPlan } from "./api";

const EXPORT_ACTIONS: ExportAction[] = [
  "copy_file",
  "create_folder",
  "remove_stale_copy",
  "preserve_deprecated",
  "skip",
];

export function ExportPanel() {
  const { selectedEnvironmentId, selectView } = useAppState();
  const [playlists, setPlaylists] = useState<PlaylistSummaryRead[]>([]);
  const [selectedPlaylistIds, setSelectedPlaylistIds] = useState<string[]>([]);
  const [plan, setPlan] = useState<ExportPlanRead | null>(null);
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState(false);
  const [isCreatingPlan, setIsCreatingPlan] = useState(false);
  const [isRefreshingPlan, setIsRefreshingPlan] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshPlaylists = useCallback(
    async (environmentId: string) => {
      setIsLoadingPlaylists(true);
      setError(null);
      try {
        setPlaylists(await listPlaylists(environmentId));
      } catch (loadError) {
        setPlaylists([]);
        setError(errorMessage(loadError));
      } finally {
        setIsLoadingPlaylists(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!selectedEnvironmentId) {
      setPlaylists([]);
      setSelectedPlaylistIds([]);
      setPlan(null);
      return;
    }
    setPlan(null);
    setSelectedPlaylistIds([]);
    void refreshPlaylists(selectedEnvironmentId);
  }, [refreshPlaylists, selectedEnvironmentId]);

  const selectedPlaylistCount =
    selectedPlaylistIds.length > 0 ? selectedPlaylistIds.length : playlists.length;

  const targetRoot = useMemo(() => planTargetRoot(plan), [plan]);

  async function handleCreatePlan() {
    if (!selectedEnvironmentId) {
      setError("Select an environment before creating an export plan.");
      return;
    }
    setIsCreatingPlan(true);
    setError(null);
    try {
      const nextPlan = await createExportPlan(selectedEnvironmentId, {
        playlist_ids: selectedPlaylistIds.length > 0 ? selectedPlaylistIds : null,
      });
      setPlan(nextPlan);
    } catch (createError) {
      setError(errorMessage(createError));
    } finally {
      setIsCreatingPlan(false);
    }
  }

  async function handleRefreshPlan() {
    if (!selectedEnvironmentId || !plan) {
      return;
    }
    setIsRefreshingPlan(true);
    setError(null);
    try {
      setPlan(await getExportPlan(selectedEnvironmentId, plan.export_plan_id));
    } catch (refreshError) {
      setError(errorMessage(refreshError));
    } finally {
      setIsRefreshingPlan(false);
    }
  }

  function handleTogglePlaylist(playlistId: string) {
    setSelectedPlaylistIds((current) =>
      current.includes(playlistId)
        ? current.filter((id) => id !== playlistId)
        : [...current, playlistId],
    );
    setPlan(null);
  }

  return (
    <div className="export-workspace">
      <header className="export-topbar">
        <div className="top-tabs" aria-label="Export context">
          <span>Environment</span>
          <span className="top-tabs__active">Export</span>
        </div>
        <div className="top-actions">
          <button
            className="icon-button"
            disabled={!plan || isRefreshingPlan}
            type="button"
            title="Refresh saved plan"
            onClick={() => {
              void handleRefreshPlan();
            }}
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      {error ? (
        <ErrorBanner
          title="Export planning error"
          message={error}
          actionLabel={selectedEnvironmentId ? "Retry playlists" : undefined}
          onAction={
            selectedEnvironmentId
              ? () => {
                  void refreshPlaylists(selectedEnvironmentId);
                }
              : undefined
          }
        />
      ) : null}

      {!selectedEnvironmentId ? (
        <Panel className="export-empty-panel">
          <EmptyState
            title="Select an environment first"
            description="Export plans are generated from imported playlists and accepted local matches in one environment."
          />
        </Panel>
      ) : (
        <main className="export-main">
          <section className="export-header">
            <div>
              <div className="export-kicker">
                <Rocket size={22} />
                <span>Export Plan Preview</span>
              </div>
              <h2>USB mirror planner</h2>
              <p>
                {plan
                  ? `Previewing ${formatNumber(selectedPlaylistCount)} playlist${
                      selectedPlaylistCount === 1 ? "" : "s"
                    } to `
                  : "Create a read-only export plan for "}
                <code>{targetRoot}</code>
              </p>
            </div>
            <div className="export-header-actions">
              <Button
                disabled={isLoadingPlaylists}
                icon={<RefreshCw size={16} />}
                onClick={() => {
                  if (selectedEnvironmentId) {
                    void refreshPlaylists(selectedEnvironmentId);
                  }
                }}
              >
                Refresh Playlists
              </Button>
              <Button
                disabled={isCreatingPlan || isLoadingPlaylists}
                icon={
                  isCreatingPlan ? (
                    <Loader2 className="spin-icon" size={16} />
                  ) : (
                    <ListChecks size={16} />
                  )
                }
                variant="primary"
                onClick={handleCreatePlan}
              >
                {isCreatingPlan ? "Creating" : "Preview Export Plan"}
              </Button>
            </div>
          </section>

          <PlaylistScopePanel
            isLoading={isLoadingPlaylists}
            playlists={playlists}
            selectedPlaylistIds={selectedPlaylistIds}
            onTogglePlaylist={handleTogglePlaylist}
            onPlanAll={() => {
              setSelectedPlaylistIds([]);
              setPlan(null);
            }}
          />

          {plan ? (
            <>
              <section className="export-count-grid" aria-label="Export plan counts">
                {EXPORT_ACTIONS.map((action) => (
                  <ExportActionCard
                    action={action}
                    count={plan.counts[action] ?? 0}
                    key={action}
                  />
                ))}
              </section>

              <ExportActionLog
                items={plan.items}
                onResolveSkips={() => selectView("matching")}
              />
            </>
          ) : (
            <Panel className="export-empty-panel">
              <EmptyState
                title="No export plan preview yet"
                description="Choose all playlists or a subset, then create a preview. The backend will inspect current matches and managed export folders without writing files."
              />
            </Panel>
          )}

          <section className="export-apply-bar" aria-label="Apply export plan">
            <div>
              <strong>Apply is intentionally locked in Wave 4.</strong>
              <span>
                This screen previews persisted plans only. Filesystem writes arrive in the next export wave.
              </span>
            </div>
            <button className="button button--primary" disabled type="button">
              <Lock size={16} />
              <span>Apply arrives in Wave 5</span>
            </button>
          </section>
        </main>
      )}
    </div>
  );
}

type PlaylistScopePanelProps = {
  isLoading: boolean;
  playlists: PlaylistSummaryRead[];
  selectedPlaylistIds: string[];
  onTogglePlaylist: (playlistId: string) => void;
  onPlanAll: () => void;
};

function PlaylistScopePanel({
  isLoading,
  playlists,
  selectedPlaylistIds,
  onTogglePlaylist,
  onPlanAll,
}: PlaylistScopePanelProps) {
  return (
    <section className="export-scope-panel">
      <div>
        <h3>Planning Scope</h3>
        <p>
          {selectedPlaylistIds.length === 0
            ? "Planning all environment playlists."
            : `Planning ${formatNumber(selectedPlaylistIds.length)} selected playlist${
                selectedPlaylistIds.length === 1 ? "" : "s"
              }.`}
        </p>
      </div>

      {isLoading ? <LoadingState label="Loading playlists" /> : null}

      {!isLoading && playlists.length === 0 ? (
        <EmptyState
          title="No playlists available"
          description="Import a SoundCloud playlist before creating an export preview."
        />
      ) : null}

      {playlists.length > 0 ? (
        <>
          <div className="export-scope-actions">
            <Button disabled={selectedPlaylistIds.length === 0} onClick={onPlanAll}>
              Plan All
            </Button>
            <span>{formatNumber(playlists.length)} playlists available</span>
          </div>
          <div className="export-playlist-list">
            {playlists.map((playlist) => (
              <label className="export-playlist-option" key={playlist.id}>
                <input
                  checked={selectedPlaylistIds.includes(playlist.id)}
                  type="checkbox"
                  onChange={() => onTogglePlaylist(playlist.id)}
                />
                <span>
                  <strong>{playlist.name}</strong>
                  <em>
                    {formatNumber(playlist.active_item_count)} active ·{" "}
                    {formatNumber(playlist.matched_count + playlist.manually_mapped_count)} matched
                  </em>
                </span>
              </label>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function ExportActionCard({ action, count }: { action: ExportAction; count: number }) {
  const meta = actionMeta(action);
  return (
    <article className={["export-action-card", `export-action-card--${meta.tone}`].join(" ")}>
      <div>
        <strong>{formatNumber(count)}</strong>
        <span>{meta.countLabel}</span>
      </div>
      {meta.icon}
      {action === "remove_stale_copy" ? <em>Remove stale managed export copy</em> : null}
    </article>
  );
}

type ExportActionLogProps = {
  items: ExportPlanItemRead[];
  onResolveSkips: () => void;
};

function ExportActionLog({ items, onResolveSkips }: ExportActionLogProps) {
  return (
    <section className="export-plan-panel">
      <header>
        <h3>Detailed Action Log</h3>
        <span>
          <Filter size={14} /> All Actions
        </span>
      </header>
      {items.length === 0 ? (
        <EmptyState
          title="This plan has no item actions"
          description="The selected playlists did not produce export work for the current repository state."
        />
      ) : (
        <div className="export-action-table-wrap">
          <table className="export-action-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Source / Reason</th>
                <th aria-label="Flow" />
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <ExportActionRow
                  index={index}
                  item={item}
                  key={`${item.action}-${item.target_path}-${index}`}
                  onResolveSkips={onResolveSkips}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ExportActionRow({
  index,
  item,
  onResolveSkips,
}: {
  index: number;
  item: ExportPlanItemRead;
  onResolveSkips: () => void;
}) {
  const meta = actionMeta(item.action);
  const sourceText = item.source_path ?? item.reason ?? "No source path";
  const targetText = item.action === "skip" ? "No action taken" : item.target_path;
  return (
    <tr className={index % 2 === 0 ? undefined : "export-action-row--alt"}>
      <td>
        <span className={["export-action-badge", `export-action-badge--${meta.tone}`].join(" ")}>
          {meta.icon}
          {meta.shortLabel}
        </span>
      </td>
      <td>
        <span className={item.action === "skip" ? "export-action-muted" : undefined} title={sourceText}>
          {sourceText}
        </span>
        {item.action === "skip" ? (
          <button className="export-inline-link" type="button" onClick={onResolveSkips}>
            Resolve in Matching Review
          </button>
        ) : null}
      </td>
      <td className="export-action-flow">
        {item.action === "skip" ? <Ban size={15} /> : <ArrowRight size={15} />}
      </td>
      <td>
        <span
          className={item.action === "remove_stale_copy" ? "export-action-remove-target" : undefined}
          title={targetText}
        >
          {targetText}
        </span>
      </td>
    </tr>
  );
}

function actionMeta(action: ExportAction): {
  countLabel: string;
  shortLabel: string;
  tone: "copy" | "create" | "remove" | "preserve" | "skip";
  icon: ReactNode;
} {
  if (action === "copy_file") {
    return {
      countLabel: "Files to Copy",
      shortLabel: "Copy",
      tone: "copy",
      icon: <Copy size={16} />,
    };
  }
  if (action === "create_folder") {
    return {
      countLabel: "Folders to Create",
      shortLabel: "Create",
      tone: "create",
      icon: <FolderPlus size={16} />,
    };
  }
  if (action === "remove_stale_copy") {
    return {
      countLabel: "Stale Files to Remove",
      shortLabel: "Remove",
      tone: "remove",
      icon: <Trash2 size={16} />,
    };
  }
  if (action === "preserve_deprecated") {
    return {
      countLabel: "Deprecated to Preserve",
      shortLabel: "Preserve",
      tone: "preserve",
      icon: <Archive size={16} />,
    };
  }
  return {
    countLabel: "Skips",
    shortLabel: "Skip",
    tone: "skip",
    icon: <Ban size={16} />,
  };
}

function planTargetRoot(plan: ExportPlanRead | null) {
  if (!plan) {
    return "_music_manager_export";
  }
  const managedPath = plan.items
    .map((item) => item.target_path)
    .find((targetPath) => targetPath.includes("_music_manager_export"));
  if (!managedPath) {
    return "Managed export folder";
  }
  const marker = "_music_manager_export";
  const markerIndex = managedPath.indexOf(marker);
  return managedPath.slice(0, markerIndex + marker.length);
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
