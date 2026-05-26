from music_manager_backend.shared.errors import (
    ApplicationError,
    DatabaseBusyError,
    DomainError,
    InfrastructureError,
    NotFoundError,
    OperationInProgressError,
    ValidationError,
)


def test_structured_error_exposes_stable_detail() -> None:
    error = DomainError("Something went wrong")

    assert error.code == "domain_error"
    assert error.message == "Something went wrong"
    assert error.to_detail().code == "domain_error"
    assert error.to_detail().message == "Something went wrong"


def test_error_subclasses_have_expected_codes() -> None:
    assert ApplicationError("x").code == "application_error"
    assert InfrastructureError("x").code == "infrastructure_error"
    assert NotFoundError("x").code == "not_found"
    assert OperationInProgressError("x").code == "operation_in_progress"
    assert DatabaseBusyError("x").code == "database_busy"
    assert ValidationError("x").code == "validation_error"
