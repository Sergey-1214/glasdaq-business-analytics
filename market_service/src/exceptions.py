class AppError(Exception):
    status_code = 500
    error_code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class IngestionError(AppError):
    status_code = 500
    error_code = "ingestion_error"


class IngestionValidationError(IngestionError):
    status_code = 400
    error_code = "ingestion_validation_error"


class IngestionConflictError(IngestionError):
    status_code = 409
    error_code = "ingestion_conflict_error"
