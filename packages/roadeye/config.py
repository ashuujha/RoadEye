from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ROADEYE_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    database_url: str = "postgresql+psycopg://roadeye:roadeye@localhost:5432/roadeye"
    demo_enabled: bool = False
    source_mode: str = "synthetic"
    demo_password: str = ""
    evidence_root: Path = Path("data/synthetic/evidence")
    accept_score: float = Field(0.8, ge=0, le=1)
    accept_margin: float = Field(0.2, ge=0, le=1)
    lease_seconds: int = Field(30, ge=1)
    max_attempts: int = Field(3, ge=1, le=10)
    cors_origin: str = "http://localhost:5173"

    @model_validator(mode="after")
    def supported(self):
        if self.source_mode != "synthetic":
            raise ValueError("Real input adapters are unavailable; source_mode must be synthetic")
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL with psycopg is required; no fallback database")
        if self.demo_enabled and len(self.demo_password) < 16:
            raise ValueError("Local demo requires ROADEYE_DEMO_PASSWORD of at least 16 characters")
        return self


settings = Settings()
