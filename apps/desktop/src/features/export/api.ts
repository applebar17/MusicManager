import { apiGet, apiPatch, apiPost } from "../../shared/api/http";
import type {
  ExportApplyRunRead,
  ExportPlanCreate,
  ExportPlanRead,
  ExportPlanUpdate,
} from "../../shared/api/types";

export function createExportPlan(environmentId: string, data: ExportPlanCreate) {
  return apiPost<ExportPlanRead, ExportPlanCreate>(
    `/environments/${environmentId}/export-plans`,
    data,
  );
}

export function getExportPlan(environmentId: string, exportPlanId: string) {
  return apiGet<ExportPlanRead>(
    `/environments/${environmentId}/export-plans/${exportPlanId}`,
  );
}

export function updateExportPlan(
  environmentId: string,
  exportPlanId: string,
  data: ExportPlanUpdate,
) {
  return apiPatch<ExportPlanRead, ExportPlanUpdate>(
    `/environments/${environmentId}/export-plans/${exportPlanId}`,
    data,
  );
}

export function applyExportPlan(environmentId: string, exportPlanId: string) {
  return apiPost<ExportApplyRunRead>(
    `/environments/${environmentId}/export-plans/${exportPlanId}/apply`,
  );
}

export function getExportApplyRun(environmentId: string, applyRunId: string) {
  return apiGet<ExportApplyRunRead>(
    `/environments/${environmentId}/export-apply-runs/${applyRunId}`,
  );
}
