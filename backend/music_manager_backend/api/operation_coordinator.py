from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock

from music_manager_backend.shared.errors import OperationInProgressError


@dataclass(frozen=True)
class ActiveOperation:
    environment_id: str
    name: str


class OperationCoordinator:
    def __init__(self) -> None:
        self._guard = Lock()
        self._locks: dict[str, Lock] = {}
        self._active: dict[str, ActiveOperation] = {}

    @contextmanager
    def guard(self, *, environment_id: str, operation_name: str) -> Iterator[None]:
        lock = self._lock_for(environment_id)
        if not lock.acquire(blocking=False):
            active = self._active.get(environment_id)
            active_name = active.name if active is not None else "another operation"
            raise OperationInProgressError(
                f"Cannot start {operation_name}: {active_name} is already running "
                f"for environment {environment_id}."
            )

        with self._guard:
            self._active[environment_id] = ActiveOperation(
                environment_id=environment_id,
                name=operation_name,
            )
        try:
            yield
        finally:
            with self._guard:
                self._active.pop(environment_id, None)
            lock.release()

    def active_operation(self, environment_id: str) -> ActiveOperation | None:
        with self._guard:
            return self._active.get(environment_id)

    def _lock_for(self, environment_id: str) -> Lock:
        with self._guard:
            lock = self._locks.get(environment_id)
            if lock is None:
                lock = Lock()
                self._locks[environment_id] = lock
            return lock
