"""
Configuration — all values read from environment variables via pydantic-settings.
Copy .env.example → .env and set values before running.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PH_FX_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    postgres_dsn: str = "postgresql://fx:fx@localhost:5432/ph_fx"
    pg_host: str = "postgres"
    pg_port: int = 5432
    pg_user: str = "fx"
    pg_password: str = "fx"
    pg_dbname: str = "ph_fx"

    alert_threshold_pct: float = 1.5   # % daily move that triggers alert
    start_year: int = 2017              # earliest year to fetch from BSP
    max_retries: int = 3
    request_timeout: int = 30

    fallback_api: str = "https://api.frankfurter.app"
    bsp_rerb_url: str = "https://www.bsp.gov.ph/statistics/external/day99_data.aspx"
    bsp_table12_url: str = "https://www.bsp.gov.ph/statistics/external/tab12_pus.aspx"
    bsp_table13_url: str = "https://www.bsp.gov.ph/statistics/external/tab13_php.aspx"

    streamlit_port: int = 8501
    adminer_port: int = 8080


settings = Settings()
