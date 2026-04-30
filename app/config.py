"""Centralised runtime settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime configuration resolved from the environment."""

    DATABASE_URL: str = "postgresql+asyncpg://appuser:changeme@localhost:5432/invasive_trace"
    INAT_API_KEY: str = ""
    EDDMAPS_API_KEY: str = ""
    PC_SDK_SUBSCRIPTION_KEY: str = ""
    GEE_PROJECT: str = ""
    GEE_ACCESS_TOKEN: str = ""
    ALPHAEARTH_COLLECTION: str = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
    LOG_LEVEL: str = "info"

    # SGI Enhancements Constants
    MAX_CONCURRENT_JOBS: int = 4
    TILE_SIZE: int = 256
    RANDOM_SEED: int = 42

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
