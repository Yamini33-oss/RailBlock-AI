"""Application configuration and environment management for KAVACH BIE Member 3."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Centralized application settings loaded from environment or .env file."""
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # Firebase Settings
    FIREBASE_PROJECT_ID: Optional[str] = "kavach-bie-dev"
    FIREBASE_STORAGE_BUCKET: Optional[str] = "kavach-bie-dev.firebasestorage.app"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    FIREBASE_AUTH_ENABLED: bool = False
    MOCK_FIREBASE: bool = True

    # External Integration Endpoints
    MEMBER2_PREDICTION_URL: str = "http://localhost:8002/api/prediction/disruption"
    MEMBER4_VALIDATION_URL: str = "http://localhost:8004/api/validation/validate"

    # Optimization Defaults
    SOLVER_TIME_LIMIT_SECONDS: float = 10.0
    STEP_MINUTES: int = 15
    MAX_VALIDATION_ATTEMPTS: int = 5
    MAX_ALTERNATIVES: int = 5

    # Directory Paths
    DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
    DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    DATA_METADATA_DIR: Path = BASE_DIR / "data" / "metadata"
    DATA_REPORTS_DIR: Path = BASE_DIR / "data" / "reports"
    DATA_SYNTHETIC_DIR: Path = BASE_DIR / "data" / "synthetic"

    @property
    def is_firebase_configured(self) -> bool:
        """Check if real Firebase credentials are provided and the file exists."""
        if not self.GOOGLE_APPLICATION_CREDENTIALS:
            return False
        creds_path = Path(self.GOOGLE_APPLICATION_CREDENTIALS)
        if not creds_path.is_absolute():
            creds_path = BASE_DIR / creds_path
        return creds_path.exists() and creds_path.is_file()


settings = Settings()
