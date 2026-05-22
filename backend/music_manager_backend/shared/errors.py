from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDetail:
    code: str
    message: str


class MusicManagerError(Exception):
    code = "music_manager_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        self.code = code or self.code
        super().__init__(message)

    def to_detail(self) -> ErrorDetail:
        return ErrorDetail(code=self.code, message=self.message)


class DomainError(MusicManagerError):
    code = "domain_error"


class ApplicationError(MusicManagerError):
    code = "application_error"


class InfrastructureError(MusicManagerError):
    code = "infrastructure_error"


class NotFoundError(ApplicationError):
    code = "not_found"


class ValidationError(ApplicationError):
    code = "validation_error"
