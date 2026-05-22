from music_manager_backend.domain.entities import ExportPlan
from music_manager_backend.ports.exporter import ExportPlanner


class PlanExport:
    def __init__(self, planner: ExportPlanner) -> None:
        self.planner = planner

    def execute(self, environment_id: str) -> ExportPlan:
        return self.planner.plan(environment_id)

