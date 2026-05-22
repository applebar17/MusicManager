from typing import Protocol

from music_manager_backend.domain.entities import ExportPlan


class ExportPlanner(Protocol):
    def plan(self, environment_id: str) -> ExportPlan:
        pass

