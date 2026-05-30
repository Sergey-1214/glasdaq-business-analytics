class AppError(Exception):
    status_code = 500
    error_code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ExternalServiceError(AppError):
    status_code = 502
    error_code = "external_service_error"


class AnalysisFormatError(AppError):
    status_code = 502
    error_code = "analysis_format_error"


class AuthError(AppError):
    status_code = 401
    error_code = "auth_error"
