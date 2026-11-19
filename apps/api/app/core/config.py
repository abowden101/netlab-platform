"""Application settings (pydantic-settings, loaded from .env)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./netlab.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    oauth_github_client_id: str = ""
    oauth_github_client_secret: str = ""
    oauth_github_redirect_uri: str = "http://localhost:8000/api/v1/auth/github/callback"
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    lab_ttl_seconds: int = 7200
    lab_idle_timeout_seconds: int = 1800
    max_labs_per_host: int = 8
    max_cpu_per_lab: float = 8.0
    max_mem_per_lab_mb: int = 8192

    containerlab_bin: str = "containerlab"
    upload_dir: str = "./uploads"
    max_image_upload_mb: int = 4096

    labs_dir: str = "./labs"
    auto_create_tables: bool = True
    console_log_dir: str = "./console-logs"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
