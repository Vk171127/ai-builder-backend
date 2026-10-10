"""Application configuration management for Gatekeeper."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Gatekeeper", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    gatekeeper_env: Literal["fake", "gcp"] = Field(default="fake", alias="GATEKEEPER_ENV")

    # API
    api_v1_prefix: str = Field(default="/v1", alias="API_V1_PREFIX")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = Field(default=True, alias="RELOAD")

    # CORS
    allowed_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="ALLOWED_ORIGINS",
    )

    @property
    def allowed_origins(self) -> list[str]:
        """Parse comma-separated CORS origins string into list."""
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # External integrations / model runtime
    gemini_model_id: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL_ID")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    policy_file: str = Field(default="policy.yaml", alias="POLICY_FILE")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"


settings = Settings()
