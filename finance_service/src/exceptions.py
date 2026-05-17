class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "bad_request"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class AuthError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, status_code=401, error_code="auth_error")
