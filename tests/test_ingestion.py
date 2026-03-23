"""
Unit tests for ingestion modules.
HTTP calls are mocked — no live BSP or Frankfurter requests made.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ph_fx.models import CrossRate, FXRate


class TestBSPRERB:
    def test_parse_daily_valid_html(self):
        from ph_fx.ingestion.bsp_rerb import _parse_daily

        html = """
        <table>
          <tr><th>Date</th><th>Rate</th></tr>
          <tr><td>03/23/2026</td><td>57.3400</td></tr>
        </table>
        """
        result = _parse_daily(html)
        assert result is not None
        assert isinstance(result, FXRate)
        assert result.currency_pair == "USD/PHP"
        assert result.rate == 57.34
        assert result.rate_date == date(2026, 3, 23)

    def test_parse_daily_empty_table(self):
        from ph_fx.ingestion.bsp_rerb import _parse_daily
        result = _parse_daily("<table><tr><th>Date</th></tr></table>")
        assert result is None

    def test_parse_date_formats(self):
        from ph_fx.ingestion.bsp_rerb import _parse_date
        assert _parse_date("03/23/2026") == date(2026, 3, 23)
        assert _parse_date("March 23, 2026") == date(2026, 3, 23)
        assert _parse_date("2026-03-23") == date(2026, 3, 23)

    def test_parse_date_invalid_raises(self):
        from ph_fx.ingestion.bsp_rerb import _parse_date
        with pytest.raises(ValueError):
            _parse_date("not-a-date")

    @patch("ph_fx.ingestion.bsp_rerb.requests.get")
    def test_fetch_daily_rate_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = """
        <table>
          <tr><th>Date</th><th>Rate</th></tr>
          <tr><td>03/23/2026</td><td>57.3400</td></tr>
        </table>"""
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from ph_fx.ingestion.bsp_rerb import fetch_daily_rate
        result = fetch_daily_rate()
        assert result is not None
        assert result.rate == 57.34


class TestBSPHistorical:
    def test_parse_table12(self):
        from ph_fx.ingestion.bsp_historical import _parse_table12

        html = """
        <table>
          <tr><th>Year</th><th>Jan</th><th>Feb</th></tr>
          <tr><td>2024</td><td>56.10</td><td>56.25</td></tr>
          <tr><td>2023</td><td>55.50</td><td>55.63</td></tr>
        </table>"""
        records = _parse_table12(html, start_year=2023)
        assert len(records) == 4
        assert all(isinstance(r, FXRate) for r in records)
        assert all(r.currency_pair == "USD/PHP" for r in records)

    def test_parse_table12_skips_before_start_year(self):
        from ph_fx.ingestion.bsp_historical import _parse_table12
        html = """
        <table>
          <tr><td>2015</td><td>45.50</td></tr>
          <tr><td>2024</td><td>56.10</td></tr>
        </table>"""
        records = _parse_table12(html, start_year=2020)
        assert all(r.rate_date.year >= 2020 for r in records)

    def test_parse_table13(self):
        from ph_fx.ingestion.bsp_historical import _parse_table13
        html = """
        <table>
          <tr><td>EUR</td><td>60.15</td></tr>
          <tr><td>JPY</td><td>0.37</td></tr>
          <tr><td>GBP</td><td>71.20</td></tr>
        </table>"""
        records = _parse_table13(html)
        assert len(records) == 3
        assert all(isinstance(r, CrossRate) for r in records)
        currencies = {r.base_currency for r in records}
        assert "EUR" in currencies
        assert "JPY" in currencies


class TestFrankfurter:
    @patch("ph_fx.ingestion.frankfurter.requests.get")
    def test_fetch_latest_usdphp_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "date": "2026-03-21",
            "rates": {"PHP": 57.10},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from ph_fx.ingestion.frankfurter import fetch_latest_usdphp
        result = fetch_latest_usdphp()
        assert result is not None
        assert result.rate == 57.10
        assert result.source == "frankfurter"

    @patch("ph_fx.ingestion.frankfurter.requests.get")
    def test_fetch_latest_returns_none_on_failure(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        from ph_fx.ingestion.frankfurter import fetch_latest_usdphp
        result = fetch_latest_usdphp()
        assert result is None
