"""
pytest fixtures shared across all test modules.
Tests that touch PostgreSQL are skipped automatically when DB is unavailable.
"""

from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests that require a live PostgreSQL connection"
    )


@pytest.fixture
def sample_fx_rate():
    from datetime import date
    from ph_fx.models import FXRate
    return FXRate(
        rate_date=date(2024, 1, 15),
        currency_pair="USD/PHP",
        rate=56.4321,
        source="bsp_rerb",
    )


@pytest.fixture
def sample_cross_rate():
    from datetime import date
    from ph_fx.models import CrossRate
    return CrossRate(
        rate_date=date(2024, 1, 15),
        base_currency="EUR",
        php_rate=61.2345,
        source="bsp_table13",
    )


@pytest.fixture
def sample_fx_rates():
    from datetime import date
    from ph_fx.models import FXRate
    return [
        FXRate(rate_date=date(2024, 1, d), currency_pair="USD/PHP",
               rate=56.0 + d * 0.05, source="bsp_rerb")
        for d in range(1, 11)
    ]
