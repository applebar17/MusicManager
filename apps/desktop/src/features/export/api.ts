import { apiGet, apiPost } from "../../shared/api/http";
import type { ExportPlanCreate, ExportPlanRead } from "../../shared/api/types";

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
