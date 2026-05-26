import pytest

from music_manager_backend.api.operation_coordinator import OperationCoordinator
from music_manager_backend.shared.errors import OperationInProgressError


def test_operation_coordinator_rejects_concurrent_operation_for_same_environment() -> None:
    coordinator = OperationCoordinator()

    with coordinator.guard(environment_id="env_1", operation_name="scan"):
        with pytest.raises(OperationInProgressError) as exc_info:
            with coordinator.guard(environment_id="env_1", operation_name="import"):
                pass

    assert "scan is already running" in exc_info.value.message


def test_operation_coordinator_releases_lock_after_exception() -> None:
    coordinator = OperationCoordinator()

    with pytest.raises(RuntimeError):
        with coordinator.guard(environment_id="env_1", operation_name="scan"):
            raise RuntimeError("boom")

    with coordinator.guard(environment_id="env_1", operation_name="import"):
        assert coordinator.active_operation("env_1") is not None
