"""ThermaCity — Application Settings

Loads configuration from environment variables / .env file.
All settings are validated at startup via Pydantic.

Heat Vulnerability Score weights are parameterised here so they
can be adjusted through stakeholder feedback without code changes.
"""

import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://postgres:ThermaCity123%40@db.ctjbapfdnyioazajfasp.supabase.co:5432/postgres"
    )

    # Synchronous URL for migrations / scripts (asyncpg → psycopg2)
    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    # ── ML Model ──────────────────────────────────────────────
    ml_model_path: str = "../ml/models/rf_lst_predictor_v1.joblib"

    # ── Google Earth Engine ───────────────────────────────────
    gee_service_account_key: str = "../credentials/thermacity-504715-08378215d2cd.json"


    # ── Heat Vulnerability Score Weights ─────────────────────
    # JSON string — parsed into dict at runtime.
    # Keys: lst, humidity, wind, population, canopy. Must sum to 1.0.
    # These defaults align with established urban climate literature:
    #   Surface heat (0.35) + human exposure (0.20) + shade deficit (0.20)
    #   + humidity amplifier (0.15) + wind stagnation (0.10) = 1.0
    hvi_weights: str = (
        '{"lst": 0.35, "humidity": 0.15, "wind": 0.10, "population": 0.20, "canopy": 0.20}'
    )

    @property
    def hvi_weight_dict(self) -> dict[str, float]:
        weights = json.loads(self.hvi_weights)
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"HVI weights must sum to 1.0, got {total}: {weights}"
            )
        return weights

    # ── Server ────────────────────────────────────────────────
    app_name: str = "ThermaCity"
    app_description: str = "Know where the heat hurts most — heat vulnerability mapping for Pune"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # CORS origins (comma-separated)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Singleton — import this throughout the app
settings = Settings()
