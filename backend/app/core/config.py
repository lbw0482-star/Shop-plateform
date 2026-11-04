from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Member Shopping Platform API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql://shop_user:shop@localhost:5432/shop_db"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    session_ttl_hours: int = 24
    upload_dir: str = "uploads"
    seed_demo_data: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

