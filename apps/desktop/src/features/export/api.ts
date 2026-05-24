import { apiGet, apiPost } from "../../shared/api/http";
import type { ExportApplyRunRead, ExportPlanCreate, ExportPlanRead } from "../../shared/api/types";

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
