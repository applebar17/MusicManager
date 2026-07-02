import {
  AlertTriangle,
  Archive,
  ArrowRight,
  Ban,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Copy,
  Filter,
  FolderPlus,
  GripVertical,
  ListChecks,
  Loader2,
  RefreshCw,
  Rocket,
  Trash2,
  XCircle,
} from "lucide-react";
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { MouseEvent, ReactNode } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  ExportAction,
  ExportApplyItemResultRead,
  ExportApplyItemStatus,
  ExportApplyRunRead,
  ExportApplyRunStatus,
  ExportPlanItemRead,
  ExportPlanRead,
  PlaylistSummaryRead,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, ConfirmDialog, EmptyState, ErrorBanner, LoadingState, Panel } from "../../shared/ui";
import { listPlaylists } from "../playlists/api";
import {
  applyExportPlan,
  createExportPlan,
  getExportApplyRun,
  getExportPlan,
  updateExportPlan,
} from "./api";

const EXPORT_ACTIONS: ExportAction[] = [
  "copy_file",
  "create_folder",
  "remove_duplicate_copy",
  "remove_stale_copy",
  "preserve_deprecated",
];

export function ExportPanel() {
  const {
    selectedEnvironmentId,
    selectedExportApplyRunId,
    selectedExportPlanId,
    selectExportApplyRun,
    selectExportPlan,
  } = useAppState();
  const [playlists, setPlaylists] = useState<PlaylistSummaryRead[]>([]);
  const [selectedPlaylistIds, setSelectedPlaylistIds] = useState<string[]>([]);
  const [plan, setPlan] = useState<ExportPlanRead | null>(null);
  const [applyRun, setApplyRun] = useState<ExportApplyRunRead | null>(null);
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState(false);
  const [isCreatingPlan, setIsCreatingPlan] = useState(false);
  const [isRefreshingPlan, setIsRefreshingPlan] = useState(false);
  const [isApplyingPlan, setIsApplyingPlan] = useState(false);
  const [isUpdatingPlan, setIsUpdatingPlan] = useState(false);
  const [isRefreshingApplyRun, setIsRefreshingApplyRun] = useState(false);
  const [isConfirmingApply, setIsConfirmingApply] = useState(false);
  const [selectedActionIds, setSelectedActionIds] = useState<Set<string>>(() => new Set());
  const [expandedActionIds, setExpandedActionIds] = useState<Set<string>>(() => new Set());
  const [lastSelectedActionId, setLastSelectedActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

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
      setApplyRun(null);
      clearActionSelection();
      return;
    }
    setSelectedPlaylistIds([]);
    clearActionSelection();
    void refreshPlaylists(selectedEnvironmentId);
  }, [refreshPlaylists, selectedEnvironmentId]);

  useEffect(() => {
    if (!selectedEnvironmentId || !selectedExportPlanId) {
      setPlan(null);
      return;
    }
    if (plan?.export_plan_id === selectedExportPlanId) {
      return;
    }
    setIsRefreshingPlan(true);
    setError(null);
    void getExportPlan(selectedEnvironmentId, selectedExportPlanId)
      .then((storedPlan) => {
        setPlan(storedPlan);
      })
      .catch((loadError: unknown) => {
        setPlan(null);
        selectExportPlan(null);
        setError(errorMessage(loadError));
      })
      .finally(() => {
        setIsRefreshingPlan(false);
      });
  }, [plan?.export_plan_id, selectedEnvironmentId, selectedExportPlanId]);

  useEffect(() => {
    if (!selectedEnvironmentId || !selectedExportApplyRunId) {
      setApplyRun(null);
      return;
    }
    if (applyRun?.apply_run_id === selectedExportApplyRunId) {
      return;
    }
    setIsRefreshingApplyRun(true);
    setError(null);
    void getExportApplyRun(selectedEnvironmentId, selectedExportApplyRunId)
      .then((storedRun) => {
        setApplyRun(storedRun);
      })
      .catch((loadError: unknown) => {
        setApplyRun(null);
        selectExportApplyRun(null);
        setError(errorMessage(loadError));
      })
      .finally(() => {
        setIsRefreshingApplyRun(false);
      });
  }, [applyRun?.apply_run_id, selectedEnvironmentId, selectedExportApplyRunId]);

  useEffect(() => {
    if (
      !selectedEnvironmentId ||
      !applyRun ||
      (applyRun.status !== "queued" && applyRun.status !== "running")
    ) {
      return;
    }
    const intervalId = window.setInterval(() => {
      void getExportApplyRun(selectedEnvironmentId, applyRun.apply_run_id)
        .then((nextRun) => {
          setApplyRun(nextRun);
        })
        .catch((pollError: unknown) => {
          setError(errorMessage(pollError));
        });
    }, 750);
    return () => window.clearInterval(intervalId);
  }, [applyRun, selectedEnvironmentId]);

  const selectedPlaylistCount =
    selectedPlaylistIds.length > 0 ? selectedPlaylistIds.length : playlists.length;

  const targetRoot = useMemo(() => planTargetRoot(plan), [plan]);
  const includedItems = useMemo(
    () => plan?.items.filter((item) => item.included) ?? [],
    [plan],
  );
  const applyResultsByPlanItemId = useMemo(() => {
    const byId = new Map<string, ExportApplyItemResultRead>();
    for (const item of applyRun?.item_results ?? []) {
      if (item.export_plan_item_id) {
        byId.set(item.export_plan_item_id, item);
      }
    }
    return byId;
  }, [applyRun?.item_results]);

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
      setApplyRun(null);
      clearActionSelection();
      selectExportApplyRun(null);
      selectExportPlan(nextPlan.export_plan_id);
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
      clearActionSelection();
    } catch (refreshError) {
      setError(errorMessage(refreshError));
    } finally {
      setIsRefreshingPlan(false);
    }
  }

  async function handleApplyPlan() {
    if (!selectedEnvironmentId || !plan) {
      return;
    }
    setIsApplyingPlan(true);
    setIsConfirmingApply(false);
    setError(null);
    try {
      const nextApplyRun = await applyExportPlan(selectedEnvironmentId, plan.export_plan_id);
      setApplyRun(nextApplyRun);
      setPlan(await getExportPlan(selectedEnvironmentId, plan.export_plan_id));
      clearActionSelection();
      selectExportPlan(nextApplyRun.export_plan_id);
      selectExportApplyRun(nextApplyRun.apply_run_id);
    } catch (applyError) {
      setError(errorMessage(applyError));
    } finally {
      setIsApplyingPlan(false);
    }
  }

  async function handleRefreshApplyRun() {
    if (!selectedEnvironmentId || !applyRun) {
      return;
    }
    setIsRefreshingApplyRun(true);
    setError(null);
    try {
      setApplyRun(await getExportApplyRun(selectedEnvironmentId, applyRun.apply_run_id));
    } catch (refreshError) {
      setError(errorMessage(refreshError));
    } finally {
      setIsRefreshingApplyRun(false);
    }
  }

  function handleTogglePlaylist(playlistId: string) {
    setSelectedPlaylistIds((current) =>
      current.includes(playlistId)
        ? current.filter((id) => id !== playlistId)
        : [...current, playlistId],
    );
    setPlan(null);
    setApplyRun(null);
    selectExportApplyRun(null);
    selectExportPlan(null);
  }

  async function persistPlanItems(includedItemIds: string[]) {
    if (!selectedEnvironmentId || !plan) {
      return;
    }
    setIsUpdatingPlan(true);
    setError(null);
    try {
      const included = new Set(includedItemIds);
      const nextPlan = await updateExportPlan(selectedEnvironmentId, plan.export_plan_id, {
        included_item_ids: includedItemIds,
        excluded_item_ids: plan.items
          .map((item) => item.export_plan_item_id)
          .filter((itemId) => !included.has(itemId)),
      });
      setPlan(nextPlan);
      setApplyRun(null);
      selectExportApplyRun(null);
      setSelectedActionIds(
        (current) =>
          new Set([...current].filter((itemId) => included.has(itemId))),
      );
    } catch (updateError) {
      setError(errorMessage(updateError));
    } finally {
      setIsUpdatingPlan(false);
    }
  }

  function handleActionSelection(
    itemId: string,
    checked: boolean,
    event: MouseEvent<HTMLInputElement>,
  ) {
    setSelectedActionIds((current) => {
      const next = new Set(current);
      if (event.shiftKey && lastSelectedActionId) {
        const ids = includedItems.map((item) => item.export_plan_item_id);
        const start = ids.indexOf(lastSelectedActionId);
        const end = ids.indexOf(itemId);
        if (start >= 0 && end >= 0) {
          const [from, to] = start < end ? [start, end] : [end, start];
          for (const rangeId of ids.slice(from, to + 1)) {
            if (checked) {
              next.add(rangeId);
            } else {
              next.delete(rangeId);
            }
          }
        }
      } else if (checked) {
        next.add(itemId);
      } else {
        next.delete(itemId);
      }
      return next;
    });
    setLastSelectedActionId(itemId);
  }

  function handleToggleExpanded(itemId: string) {
    setExpandedActionIds((current) => {
      const next = new Set(current);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id || !plan || plan.locked_at) {
      return;
    }
    const activeId = String(active.id);
    const overId = String(over.id);
    const currentIds = includedItems.map((item) => item.export_plan_item_id);
    const movingIds = selectedActionIds.has(activeId)
      ? new Set([...selectedActionIds].filter((itemId) => currentIds.includes(itemId)))
      : new Set([activeId]);
    if (movingIds.has(overId)) {
      return;
    }
    const movingBlock = currentIds.filter((itemId) => movingIds.has(itemId));
    const remaining = currentIds.filter((itemId) => !movingIds.has(itemId));
    const insertAt = remaining.indexOf(overId);
    if (insertAt < 0) {
      return;
    }
    const nextIds = [
      ...remaining.slice(0, insertAt),
      ...movingBlock,
      ...remaining.slice(insertAt),
    ];
    void persistPlanItems(nextIds);
  }

  function handleDeleteSelectedActions() {
    if (selectedActionIds.size === 0 || !plan || plan.locked_at) {
      return;
    }
    const nextIncludedIds = includedItems
      .map((item) => item.export_plan_item_id)
      .filter((itemId) => !selectedActionIds.has(itemId));
    void persistPlanItems(nextIncludedIds);
  }

  function clearActionSelection() {
    setSelectedActionIds(new Set());
    setExpandedActionIds(new Set());
    setLastSelectedActionId(null);
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
              setApplyRun(null);
              selectExportApplyRun(null);
              selectExportPlan(null);
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
                applyResultsByPlanItemId={applyResultsByPlanItemId}
                expandedActionIds={expandedActionIds}
                isLocked={Boolean(plan.locked_at)}
                isUpdating={isUpdatingPlan}
                items={includedItems}
                selectedActionIds={selectedActionIds}
                sensors={sensors}
                validationMessage={plan.validation_error_message}
                onDeleteSelected={handleDeleteSelectedActions}
                onDragEnd={handleDragEnd}
                onSelectAction={handleActionSelection}
                onToggleExpanded={handleToggleExpanded}
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

          <ExportApplyBar
            applyRun={applyRun}
            disabled={
              !plan ||
              isApplyingPlan ||
              !plan.is_valid ||
              Boolean(plan.locked_at) ||
              Boolean(applyRun)
            }
            isApplying={isApplyingPlan}
            onApply={() => setIsConfirmingApply(true)}
          />
        </main>
      )}
      <ConfirmDialog
        confirmLabel="Apply Export Plan"
        message={
          "This will lock the current plan and write files inside the managed export folder using the row order shown above. Create a fresh preview after meaningful library or match changes."
        }
        open={isConfirmingApply}
        title="Apply this export plan?"
        onCancel={() => setIsConfirmingApply(false)}
        onConfirm={() => {
          void handleApplyPlan();
        }}
      />
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
      {action === "remove_duplicate_copy" ? <em>Remove duplicate local copy</em> : null}
      {action === "remove_stale_copy" ? <em>Remove stale app-owned export copy</em> : null}
    </article>
  );
}

type ExportActionLogProps = {
  items: ExportPlanItemRead[];
  selectedActionIds: Set<string>;
  expandedActionIds: Set<string>;
  applyResultsByPlanItemId: Map<string, ExportApplyItemResultRead>;
  isLocked: boolean;
  isUpdating: boolean;
  sensors: ReturnType<typeof useSensors>;
  validationMessage: string | null;
  onDeleteSelected: () => void;
  onDragEnd: (event: DragEndEvent) => void;
  onSelectAction: (
    itemId: string,
    checked: boolean,
    event: MouseEvent<HTMLInputElement>,
  ) => void;
  onToggleExpanded: (itemId: string) => void;
};

function ExportActionLog({
  items,
  selectedActionIds,
  expandedActionIds,
  applyResultsByPlanItemId,
  isLocked,
  isUpdating,
  sensors,
  validationMessage,
  onDeleteSelected,
  onDragEnd,
  onSelectAction,
  onToggleExpanded,
}: ExportActionLogProps) {
  const selectedCount = selectedActionIds.size;
  return (
    <section className="export-plan-panel">
      <header>
        <h3>Filesystem Changes</h3>
        <span>
          <Filter size={14} /> {isLocked ? "Locked Plan" : "Editable Plan"}
        </span>
      </header>
      <div className="export-plan-toolbar">
        <span>
          {formatNumber(items.length)} actions / {formatNumber(selectedCount)} selected
        </span>
        <Button
          disabled={selectedCount === 0 || isLocked || isUpdating}
          icon={isUpdating ? <Loader2 className="spin-icon" size={16} /> : <Trash2 size={16} />}
          onClick={onDeleteSelected}
        >
          Delete Selected
        </Button>
      </div>
      {validationMessage ? (
        <div className="export-plan-validation">
          <AlertTriangle size={16} />
          <span>{validationMessage}</span>
        </div>
      ) : null}
      {items.length === 0 ? (
        <EmptyState
          title="No filesystem changes required"
          description="The selected playlists already match the current managed export state."
        />
      ) : (
        <DndContext collisionDetection={closestCenter} sensors={sensors} onDragEnd={onDragEnd}>
          <SortableContext
            items={items.map((item) => item.export_plan_item_id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="export-action-list">
              {items.map((item, index) => (
                <SortableExportActionRow
                  applyResult={applyResultsByPlanItemId.get(item.export_plan_item_id) ?? null}
                  expanded={expandedActionIds.has(item.export_plan_item_id)}
                  index={index}
                  isLocked={isLocked}
                  isSelected={selectedActionIds.has(item.export_plan_item_id)}
                  isUpdating={isUpdating}
                  item={item}
                  key={item.export_plan_item_id}
                  onSelectAction={onSelectAction}
                  onToggleExpanded={onToggleExpanded}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}
    </section>
  );
}

type SortableExportActionRowProps = {
  item: ExportPlanItemRead;
  applyResult: ExportApplyItemResultRead | null;
  index: number;
  isSelected: boolean;
  isLocked: boolean;
  isUpdating: boolean;
  expanded: boolean;
  onSelectAction: (
    itemId: string,
    checked: boolean,
    event: MouseEvent<HTMLInputElement>,
  ) => void;
  onToggleExpanded: (itemId: string) => void;
};

function SortableExportActionRow({
  item,
  applyResult,
  index,
  isSelected,
  isLocked,
  isUpdating,
  expanded,
  onSelectAction,
  onToggleExpanded,
}: SortableExportActionRowProps) {
  const sortable = useSortable({ id: item.export_plan_item_id, disabled: isLocked || isUpdating });
  const action = actionMeta(item.action);
  const status = applyResult ? applyItemStatusMeta(applyResult.status) : null;
  const sourceText = item.source_path ?? item.reason ?? "No source path";
  const hasDetails =
    Boolean(item.validation_error_message) ||
    Boolean(applyResult?.error_message) ||
    Boolean(applyResult?.error_code);
  const style = {
    transform: CSS.Transform.toString(sortable.transform),
    transition: sortable.transition,
  };

  return (
    <article
      className={[
        "export-action-list-row",
        index % 2 === 0 ? undefined : "export-action-list-row--alt",
        isSelected ? "is-selected" : undefined,
        item.validation_error_code ? "has-validation-error" : undefined,
        applyResult?.status === "failed" ? "has-apply-error" : undefined,
      ]
        .filter(Boolean)
        .join(" ")}
      ref={sortable.setNodeRef}
      style={style}
    >
      <div className="export-action-list-row__main">
        <button
          className="export-row-icon-button"
          disabled={isLocked || isUpdating}
          type="button"
          title="Drag action"
          {...sortable.attributes}
          {...sortable.listeners}
        >
          <GripVertical size={16} />
        </button>
        <input
          checked={isSelected}
          disabled={isLocked || isUpdating}
          readOnly
          type="checkbox"
          aria-label={`Select ${action.shortLabel} action`}
          onClick={(event) => {
            onSelectAction(item.export_plan_item_id, event.currentTarget.checked, event);
          }}
        />
        <span className="export-action-position">{item.position + 1}</span>
        <span className={["export-action-badge", `export-action-badge--${action.tone}`].join(" ")}>
          {action.icon}
          {action.shortLabel}
        </span>
        <span className="export-action-list-row__path" title={sourceText}>
          {sourceText}
        </span>
        <ArrowRight className="export-action-list-row__flow" size={15} />
        <span
          className={[
            "export-action-list-row__path",
            item.action === "remove_duplicate_copy" || item.action === "remove_stale_copy"
              ? "export-action-remove-target"
              : undefined,
          ]
            .filter(Boolean)
            .join(" ")}
          title={item.target_path}
        >
          {item.target_path}
        </span>
        {status ? (
          <span className={["export-result-status", `export-result-status--${status.tone}`].join(" ")}>
            {status.icon}
            {status.shortLabel}
          </span>
        ) : null}
        <button
          className="export-row-icon-button"
          disabled={!hasDetails}
          type="button"
          title="Action details"
          onClick={() => onToggleExpanded(item.export_plan_item_id)}
        >
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
      </div>
      {expanded && hasDetails ? (
        <div className="export-action-list-row__details">
          {item.validation_error_message ? (
            <p>
              <strong>{item.validation_error_code}</strong> {item.validation_error_message}
            </p>
          ) : null}
          {applyResult?.error_message || applyResult?.error_code ? (
            <p>
              <strong>{applyResult.error_code ?? "apply_error"}</strong>{" "}
              {applyResult.error_message ?? "The action failed while applying."}
            </p>
          ) : null}
          <dl>
            <div>
              <dt>Source</dt>
              <dd>{sourceText}</dd>
            </div>
            <div>
              <dt>Target</dt>
              <dd>{item.target_path}</dd>
            </div>
          </dl>
        </div>
      ) : null}
    </article>
  );
}

type ExportApplyBarProps = {
  applyRun: ExportApplyRunRead | null;
  disabled: boolean;
  isApplying: boolean;
  onApply: () => void;
};

function ExportApplyBar({ applyRun, disabled, isApplying, onApply }: ExportApplyBarProps) {
  const isRunning = applyRun?.status === "queued" || applyRun?.status === "running";
  return (
    <section className="export-apply-bar" aria-label="Apply export plan">
      <div>
        <strong>
          {applyRun
            ? isRunning
              ? "Export apply is running."
              : "This plan is locked after apply."
            : "Ready to commit the previewed plan."}
        </strong>
        <span>
          {applyRun
            ? "Create a fresh preview for any further order or removal changes."
            : "Applying writes only through the backend using the saved action order above. No fresh plan is generated implicitly."}
        </span>
      </div>
      <Button
        disabled={disabled}
        icon={isApplying ? <Loader2 className="spin-icon" size={16} /> : <CheckCircle2 size={16} />}
        variant="primary"
        onClick={onApply}
      >
        {isApplying ? "Starting" : "Apply Export Plan"}
      </Button>
    </section>
  );
}

type ExportApplyResultsProps = {
  applyRun: ExportApplyRunRead;
  isRefreshing: boolean;
  onRefresh: () => void;
};

function ExportApplyResults({ applyRun, isRefreshing, onRefresh }: ExportApplyResultsProps) {
  const status = applyRunStatusMeta(applyRun.status);
  const changeResults = applyRun.item_results.filter((item) => isChangeAction(item.action));
  const changeCounts = countApplyStatuses(changeResults);
  return (
    <section className={["export-apply-results", `export-apply-results--${status.tone}`].join(" ")}>
      <header>
        <div>
          <h3>{status.label}</h3>
          <p>
            Apply run <code>{applyRun.apply_run_id}</code> for plan{" "}
            <code>{applyRun.export_plan_id}</code>
          </p>
        </div>
        <Button
          disabled={isRefreshing}
          icon={isRefreshing ? <Loader2 className="spin-icon" size={16} /> : <RefreshCw size={16} />}
          onClick={onRefresh}
        >
          Refresh Results
        </Button>
      </header>

      <div className="export-result-count-grid" aria-label="Export apply result counts">
        {(["succeeded", "failed"] as ExportApplyItemStatus[]).map((statusKey) => (
          <ExportResultCountCard
            count={changeCounts[statusKey] ?? 0}
            key={statusKey}
            status={statusKey}
          />
        ))}
      </div>

      {changeResults.length === 0 ? (
        <EmptyState
          title="No filesystem changes were applied"
          description="This run did not contain copy, create, stale removal, or deprecated preservation work."
        />
      ) : (
        <div className="export-action-table-wrap">
          <table className="export-action-table export-result-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Action</th>
                <th>Source / Error</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {changeResults.map((item, index) => (
                <ExportApplyResultRow
                  index={index}
                  item={item}
                  key={`${item.status}-${item.action}-${item.target_path}-${index}`}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ExportResultCountCard({
  count,
  status,
}: {
  count: number;
  status: ExportApplyItemStatus;
}) {
  const meta = applyItemStatusMeta(status);
  return (
    <article className={["export-result-count-card", `export-result-count-card--${meta.tone}`].join(" ")}>
      {meta.icon}
      <strong>{formatNumber(count)}</strong>
      <span>{meta.countLabel}</span>
    </article>
  );
}

function ExportApplyResultRow({
  index,
  item,
}: {
  index: number;
  item: ExportApplyItemResultRead;
}) {
  const action = actionMeta(item.action);
  const status = applyItemStatusMeta(item.status);
  const sourceText = item.source_path ?? item.error_message ?? item.error_code ?? "No source path";
  const detailText = item.error_message ?? item.error_code;
  return (
    <tr
      className={[
        index % 2 === 0 ? undefined : "export-action-row--alt",
        `export-result-row--${status.tone}`,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <td>
        <span className={["export-result-status", `export-result-status--${status.tone}`].join(" ")}>
          {status.icon}
          {status.shortLabel}
        </span>
      </td>
      <td>
        <span className={["export-action-badge", `export-action-badge--${action.tone}`].join(" ")}>
          {action.icon}
          {action.shortLabel}
        </span>
      </td>
      <td>
        <span
          className={item.status === "skipped" ? "export-action-muted" : undefined}
          title={sourceText}
        >
          {sourceText}
        </span>
        {detailText ? <em className="export-result-error">{detailText}</em> : null}
      </td>
      <td>
        <span title={item.target_path}>{item.target_path}</span>
      </td>
    </tr>
  );
}

function ExportActionRow({
  index,
  item,
}: {
  index: number;
  item: ExportPlanItemRead;
}) {
  const meta = actionMeta(item.action);
  const sourceText = item.source_path ?? item.reason ?? "No source path";
  return (
    <tr className={index % 2 === 0 ? undefined : "export-action-row--alt"}>
      <td>
        <span className={["export-action-badge", `export-action-badge--${meta.tone}`].join(" ")}>
          {meta.icon}
          {meta.shortLabel}
        </span>
      </td>
      <td>
        <span title={sourceText}>{sourceText}</span>
      </td>
      <td className="export-action-flow">
        <ArrowRight size={15} />
      </td>
      <td>
        <span
          className={
            item.action === "remove_duplicate_copy" || item.action === "remove_stale_copy"
              ? "export-action-remove-target"
              : undefined
          }
          title={item.target_path}
        >
          {item.target_path}
        </span>
      </td>
    </tr>
  );
}

function applyRunStatusMeta(status: ExportApplyRunStatus): {
  label: string;
  tone: "success" | "warning" | "danger";
} {
  if (status === "queued") {
    return { label: "Export queued", tone: "warning" };
  }
  if (status === "running") {
    return { label: "Export running", tone: "warning" };
  }
  if (status === "completed") {
    return { label: "Export completed", tone: "success" };
  }
  if (status === "completed_with_failures") {
    return { label: "Export completed with failures", tone: "warning" };
  }
  return { label: "Export failed", tone: "danger" };
}

function applyItemStatusMeta(status: ExportApplyItemStatus): {
  countLabel: string;
  shortLabel: string;
  tone: "success" | "warning" | "danger";
  icon: ReactNode;
} {
  if (status === "pending") {
    return {
      countLabel: "Pending",
      shortLabel: "Pending",
      tone: "warning",
      icon: <Loader2 size={16} />,
    };
  }
  if (status === "running") {
    return {
      countLabel: "Running",
      shortLabel: "Running",
      tone: "warning",
      icon: <Loader2 className="spin-icon" size={16} />,
    };
  }
  if (status === "succeeded") {
    return {
      countLabel: "Succeeded",
      shortLabel: "Succeeded",
      tone: "success",
      icon: <CheckCircle2 size={16} />,
    };
  }
  if (status === "skipped") {
    return {
      countLabel: "Skipped",
      shortLabel: "Skipped",
      tone: "warning",
      icon: <AlertTriangle size={16} />,
    };
  }
  return {
    countLabel: "Failed",
    shortLabel: "Failed",
    tone: "danger",
    icon: <XCircle size={16} />,
  };
}

function actionMeta(action: ExportAction): {
  countLabel: string;
  shortLabel: string;
  tone: "copy" | "create" | "keep" | "remove" | "preserve" | "skip";
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
  if (action === "keep_existing") {
    return {
      countLabel: "Already in Place",
      shortLabel: "Keep",
      tone: "keep",
      icon: <CheckCircle2 size={16} />,
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
  if (action === "remove_duplicate_copy") {
    return {
      countLabel: "Duplicates to Remove",
      shortLabel: "Duplicate",
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

function isChangeAction(action: ExportAction) {
  return (
    action === "copy_file" ||
    action === "create_folder" ||
    action === "remove_duplicate_copy" ||
    action === "remove_stale_copy" ||
    action === "preserve_deprecated"
  );
}

function countApplyStatuses(items: ExportApplyItemResultRead[]) {
  return items.reduce<Record<ExportApplyItemStatus, number>>(
    (counts, item) => {
      counts[item.status] += 1;
      return counts;
    },
    { pending: 0, running: 0, succeeded: 0, failed: 0, skipped: 0 },
  );
}

function planTargetRoot(plan: ExportPlanRead | null) {
  if (!plan) {
    return "Export target";
  }
  const metadataPath = plan.items
    .map((item) => item.target_path)
    .find((targetPath) => targetPath.includes("_music_manager"));
  if (metadataPath) {
    const marker = "_music_manager";
    const markerIndex = metadataPath.indexOf(marker);
    return metadataPath.slice(0, markerIndex).replace(/[\\/]+$/, "") || "/";
  }
  const firstTarget = plan.items[0]?.target_path;
  const firstItem = plan.items[0];
  if (!firstTarget || !firstItem) {
    return "Export target";
  }
  if (firstItem.action === "copy_file" || firstItem.action === "remove_stale_copy") {
    const playlistFolder = parentPath(firstTarget);
    return parentPath(playlistFolder) || playlistFolder || firstTarget;
  }
  return parentPath(firstTarget) || firstTarget;
}

function parentPath(path: string) {
  return path.replace(/[\\/]+$/, "").replace(/[\\/][^\\/]*$/, "");
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
