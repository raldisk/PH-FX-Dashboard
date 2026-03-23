"""Unit tests for Pydantic v2 domain models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from ph_fx.models import CPIRecord, CrossRate, FXRate


class TestFXRate:
    def test_valid(self):
        r = FXRate(rate_date=date(2024, 1, 1), currency_pair="USD/PHP",
                   rate=56.4, source="bsp_rerb")
        assert r.currency_pair == "USD/PHP"
        assert r.rate == 56.4

    def test_normalizes_currency_pair_lowercase(self):
        r = FXRate(rate_date=date(2024, 1, 1), currency_pair="usd/php",
                   rate=56.4, source="bsp_rerb")
        assert r.currency_pair == "USD/PHP"

    def test_rejects_zero_rate(self):
        with pytest.raises(ValidationError):
            FXRate(rate_date=date(2024, 1, 1), currency_pair="USD/PHP",
                   rate=0.0, source="bsp_rerb")

    def test_rejects_negative_rate(self):
        with pytest.raises(ValidationError):
            FXRate(rate_date=date(2024, 1, 1), currency_pair="USD/PHP",
                   rate=-1.0, source="bsp_rerb")

    def test_rejects_invalid_pair_format(self):
        with pytest.raises(ValidationError):
            FXRate(rate_date=date(2024, 1, 1), currency_pair="USDPHP",
                   rate=56.4, source="bsp_rerb")

    def test_rounds_to_4_decimals(self):
        r = FXRate(rate_date=date(2024, 1, 1), currency_pair="USD/PHP",
                   rate=56.123456789, source="bsp_rerb")
        assert r.rate == 56.1235


class TestCrossRate:
    def test_valid(self):
        r = CrossRate(rate_date=date(2024, 1, 1), base_currency="EUR",
                      php_rate=61.5, source="bsp_table13")
        assert r.base_currency == "EUR"

    def test_normalizes_lowercase(self):
        r = CrossRate(rate_date=date(2024, 1, 1), base_currency="eur",
                      php_rate=61.5, source="bsp_table13")
        assert r.base_currency == "EUR"

    def test_rejects_zero_rate(self):
        with pytest.raises(ValidationError):
            CrossRate(rate_date=date(2024, 1, 1), base_currency="EUR",
                      php_rate=0.0, source="bsp_table13")


class TestCPIRecord:
    def test_valid(self):
        r = CPIRecord(period_date=date(2024, 1, 1), cpi_index=118.5,
                      inflation_pct=2.8, source="psa_openstat")
        assert r.cpi_index == 118.5

    def test_optional_inflation_pct(self):
        r = CPIRecord(period_date=date(2024, 1, 1), cpi_index=118.5,
                      source="psa_openstat")
        assert r.inflation_pct is None
