"""
BSP historical FX scraper — Table 12 (USD/PHP monthly) and Table 13 (cross rates).
Source:
  Table 12: https://www.bsp.gov.ph/statistics/external/tab12_pus.aspx
  Table 13: https://www.bsp.gov.ph/statistics/external/tab13_php.aspx
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import List

import requests
from bs4 import BeautifulSoup

from ph_fx.config import settings
from ph_fx.models import CrossRate, FXRate

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ph-fx-dashboard/1.0; "
        "+https://github.com/raldisk/ph-fx-dashboard)"
    )
}

CROSS_CURRENCIES = ["EUR", "JPY", "GBP", "SGD", "AUD", "HKD", "CAD", "CNY"]


def fetch_monthly_usdphp(start_year: int = 2017) -> List[FXRate]:
    """
    Scrape BSP Table 12 — monthly average USD/PHP from start_year to present.
    Returns list of FXRate records.
    """
    records: List[FXRate] = []
    for attempt in range(1, settings.max_retries + 1):
        try:
            resp = requests.get(
                settings.bsp_table12_url,
                headers=HEADERS,
                timeout=settings.request_timeout,
            )
            resp.raise_for_status()
            records = _parse_table12(resp.text, start_year)
            logger.info("Table 12: fetched %d monthly records.", len(records))
            return records
        except requests.RequestException as e:
            logger.warning("Table 12 attempt %d/%d: %s", attempt, settings.max_retries, e)
            if attempt < settings.max_retries:
                time.sleep(2 ** attempt)
    return records


def fetch_cross_rates() -> List[CrossRate]:
    """
    Scrape BSP Table 13 — latest cross rates vs PHP.
    Returns list of CrossRate records.
    """
    records: List[CrossRate] = []
    for attempt in range(1, settings.max_retries + 1):
        try:
            resp = requests.get(
                settings.bsp_table13_url,
                headers=HEADERS,
                timeout=settings.request_timeout,
            )
            resp.raise_for_status()
            records = _parse_table13(resp.text)
            logger.info("Table 13: fetched %d cross rate records.", len(records))
            return records
        except requests.RequestException as e:
            logger.warning("Table 13 attempt %d/%d: %s", attempt, settings.max_retries, e)
            if attempt < settings.max_retries:
                time.sleep(2 ** attempt)
    return records


def _parse_table12(html: str, start_year: int) -> List[FXRate]:
    """
    Parse Table 12 HTML. Structure: rows of (Year, Jan, Feb, ... Dec).
    Returns one FXRate per month for each year >= start_year.
    """
    soup = BeautifulSoup(html, "html.parser")
    records = []
    MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    rows = soup.select("table tr")
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if not cells:
            continue
        try:
            year = int(cells[0])
        except ValueError:
            continue
        if year < start_year:
            continue

        for i, month_name in enumerate(MONTHS):
            if i + 1 >= len(cells):
                break
            raw = cells[i + 1].replace(",", "").strip()
            if not raw or raw == "-":
                continue
            try:
                rate_val  = float(raw)
                rate_date = date(year, i + 1, 1)
                records.append(FXRate(
                    rate_date=rate_date,
                    currency_pair="USD/PHP",
                    rate=rate_val,
                    source="bsp_table12",
                ))
            except ValueError:
                continue
    return records


def _parse_table13(html: str) -> List[CrossRate]:
    """
    Parse Table 13 HTML — latest cross rates vs PHP.
    Extracts one CrossRate per currency for the most recent date available.
    """
    soup = BeautifulSoup(html, "html.parser")
    records = []

    rows = soup.select("table tr")
    ref_date = date.today()

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 2:
            continue
        currency = cells[0].upper().strip()
        if currency not in CROSS_CURRENCIES:
            continue
        raw = cells[1].replace(",", "").strip()
        try:
            php_rate = float(raw)
            records.append(CrossRate(
                rate_date=ref_date,
                base_currency=currency,
                php_rate=php_rate,
                source="bsp_table13",
            ))
        except ValueError:
            continue
    return records
