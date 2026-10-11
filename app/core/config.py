"""Application configuration management for Gatekeeper."""

from typing import Literal

from pydantic import AliasChoices, Field
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

    # GCP (credentials come from Application Default Credentials: the runtime
    # service account when deployed, `gcloud auth application-default login` locally)
    gcp_project: str = Field(default="", validation_alias=AliasChoices("GOOGLE_CLOUD_PROJECT", "GCP_PROJECT"))
    gcp_location: str = Field(default="us-central1", validation_alias=AliasChoices("GCP_REGION", "GCP_LOCATION"))
    gemini_model_id: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL_ID")
    bigquery_dataset: str = Field(default="gatekeeper", alias="BIGQUERY_DATASET")
    pubsub_topic: str = Field(default="decisions", alias="PUBSUB_TOPIC")
    pubsub_topic_decisions: str = Field(default="", alias="PUBSUB_TOPIC_DECISIONS")
    pubsub_topic_outcomes: str = Field(default="", alias="PUBSUB_TOPIC_OUTCOMES")

    # State store (Firestore)
    state_backend: Literal["memory", "firestore"] = Field(default="memory", alias="STATE_BACKEND")
    firestore_project_id: str = Field(default="", alias="FIRESTORE_PROJECT_ID")
    firestore_database: str = Field(default="(default)", alias="FIRESTORE_DATABASE")
    firestore_analyses_collection: str = Field(default="analyses", alias="FIRESTORE_ANALYSES_COLLECTION")
    firestore_collection_prefix: str = Field(default="gatekeeper_state", alias="FIRESTORE_COLLECTION_PREFIX")

    policy_file: str = Field(default="policy.yaml", alias="POLICY_FILE")
    reasoner_warmup_timeout_ms: int = Field(default=7000, alias="REASONER_WARMUP_TIMEOUT_MS")
    reasoner_warmup_fail_open_static: bool = Field(default=True, alias="REASONER_WARMUP_FAIL_OPEN_STATIC")
    reasoner_warmup_use_llm: bool = Field(default=False, alias="REASONER_WARMUP_USE_LLM")

    @property
    def effective_pubsub_topic_decisions(self) -> str:
        return self.pubsub_topic_decisions.strip() or self.pubsub_topic

    @property
    def effective_pubsub_topic_outcomes(self) -> str:
        return self.pubsub_topic_outcomes.strip() or self.pubsub_topic

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"


settings = Settings()
