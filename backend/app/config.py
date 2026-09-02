from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "نظام إدارة المخزن"
    environment: str = "development"
    database_url: str
    session_secret: str
    session_cookie_name: str = "warehouse_session"
    session_ttl_hours: int = 8
    cors_origins: str = ""
    backup_directory: str = "/tmp/warehouse-management-backups"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
