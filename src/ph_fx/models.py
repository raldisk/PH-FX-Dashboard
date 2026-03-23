"""
Pydantic v2 domain models for FX rate data.
Every record from every source is validated here before hitting the database.
Invalid records are logged and skipped — not silently corrupted.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FXRate(BaseModel):
    """Single daily FX rate observation."""

    rate_date: date
    currency_pair: str = Field(..., pattern=r"^[A-Z]{3}/PHP$")
    rate: float = Field(..., gt=0)
    source: str  # 'bsp_rerb' | 'bsp_historical' | 'frankfurter'

    @field_validator("currency_pair")
    @classmethod
    def normalize_pair(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("rate")
    @classmethod
    def round_rate(cls, v: float) -> float:
        return round(v, 4)


class CrossRate(BaseModel):
    """Single daily cross-rate observation (non-USD currencies vs PHP)."""

    rate_date: date
    base_currency: str = Field(..., min_length=3, max_length=3)
    php_rate: float = Field(..., gt=0)
    source: str = "bsp_table13"

    @field_validator("base_currency")
    @classmethod
    def uppercase(cls, v: str) -> str:
        return v.upper().strip()


class CPIRecord(BaseModel):
    """Monthly CPI reading for real exchange rate computation."""

    period_date: date
    cpi_index: float = Field(..., gt=0)
    inflation_pct: Optional[float] = None
    source: str = "psa_openstat"
