"""
Unit tests for loader module.
Integration tests (marked) require a live PostgreSQL connection.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ph_fx.models import CrossRate, FXRate


class TestUpsertFXRates:
    def test_empty_list_returns_zero(self):
        from ph_fx.loader import upsert_fx_rates
        with patch("ph_fx.loader.get_connection"):
            result = upsert_fx_rates([])
        assert result == 0

    def test_returns_count_of_records(self, sample_fx_rates):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_conn.cursor.return_value
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("ph_fx.loader.get_connection", return_value=mock_conn):
            with patch("ph_fx.loader.psycopg2.extras.execute_values"):
                from ph_fx.loader import upsert_fx_rates
                result = upsert_fx_rates(sample_fx_rates)
        assert result == len(sample_fx_rates)


class TestUpsertCrossRates:
    def test_empty_list_returns_zero(self):
        from ph_fx.loader import upsert_cross_rates
        with patch("ph_fx.loader.get_connection"):
            result = upsert_cross_rates([])
        assert result == 0


class TestRowCounts:
    @pytest.mark.integration
    def test_row_counts_returns_dict(self):
        from ph_fx.loader import row_counts
        counts = row_counts()
        assert isinstance(counts, dict)
        assert "raw.fx_daily" in counts
        assert "raw.cross_rates" in counts
        assert "raw.cpi_monthly" in counts
