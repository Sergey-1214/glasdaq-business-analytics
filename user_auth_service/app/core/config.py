from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "user_auth_service"
    port: int = 8007
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@user-auth-db:5432/user_auth_db"
    )
    jwt_secret: str = "change_me_please"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "user_auth_service"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    log_level: str = "INFO"


settings = Settings()
