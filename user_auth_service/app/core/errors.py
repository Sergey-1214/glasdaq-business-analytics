class ServiceError(Exception):
    status_code = 400
    detail = "service error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.detail)
        self.detail = detail or self.detail


class UserAlreadyExistsError(ServiceError):
    status_code = 409
    detail = "user with this email or username already exists"


class UsernameAlreadyExistsError(ServiceError):
    status_code = 409
    detail = "username already exists"


class EmailAlreadyExistsError(ServiceError):
    status_code = 409
    detail = "email already exists"


class InvalidCredentialsError(ServiceError):
    status_code = 401
    detail = "invalid credentials"


class InvalidTokenError(ServiceError):
    status_code = 401
    detail = "invalid token"


class InvalidRefreshTokenError(ServiceError):
    status_code = 401
    detail = "invalid refresh token"


class RefreshTokenExpiredError(ServiceError):
    status_code = 401
    detail = "refresh token expired"


class UserNotFoundError(ServiceError):
    status_code = 404
    detail = "user not found"


class EmptyUpdateError(ServiceError):
    status_code = 400
    detail = "no fields provided"
