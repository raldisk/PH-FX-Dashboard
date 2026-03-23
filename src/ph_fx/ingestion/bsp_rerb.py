"""
BSP RERB daily scraper.
Fetches the USD/PHP daily rate from BSP's static HTML table.
BSP uses static HTML — no API key required.
Source: https://www.bsp.gov.ph/statistics/external/day99_data.aspx
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ph_fx.config import settings
from ph_fx.models import FXRate

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ph-fx-dashboard/1.0; "
        "+https://github.com/raldisk/ph-fx-dashboard)"
    )
}


def fetch_daily_rate() -> Optional[FXRate]:
    """
    Fetch today's USD/PHP rate from BSP's daily table.
    Returns None if BSP is unavailable or rate is not yet published.
    """
    for attempt in range(1, settings.max_retries + 1):
        try:
            resp = requests.get(
                settings.bsp_rerb_url,
                headers=HEADERS,
                timeout=settings.request_timeout,
            )
            resp.raise_for_status()
            return _parse_daily(resp.text)
        except requests.RequestException as e:
            logger.warning("BSP RERB attempt %d/%d failed: %s", attempt, settings.max_retries, e)
            if attempt < settings.max_retries:
                time.sleep(2 ** attempt)
    return None


def _parse_daily(html: str) -> Optional[FXRate]:
    """
    Parse the BSP day99_data.aspx HTML table.
    The page contains a table with date + USD/PHP rate rows.
    Returns the most recent row as an FXRate.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tr")

    for row in rows[1:]:  # skip header
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 2:
            continue
        try:
            rate_date = _parse_date(cells[0])
            rate_val  = float(cells[1].replace(",", ""))
            return FXRate(
                rate_date=rate_date,
                currency_pair="USD/PHP",
                rate=rate_val,
                source="bsp_rerb",
            )
        except (ValueError, IndexError):
            continue
    return None


def _parse_date(raw: str) -> date:
    for fmt in ("%m/%d/%Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {raw!r}")
