"""
Frankfurter API fallback — free, no API key required.
Used when BSP site is unavailable or under maintenance.
Source: https://api.frankfurter.app (ECB reference rates)
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import List, Optional

import requests

from ph_fx.config import settings
from ph_fx.models import FXRate

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = ["EUR", "JPY", "GBP", "SGD", "AUD", "HKD", "CAD", "CNY"]


def fetch_latest_usdphp() -> Optional[FXRate]:
    """
    Fetch latest USD/PHP from Frankfurter API.
    Note: Frankfurter uses EUR as base — we convert via USD.
    """
    url = f"{settings.fallback_api}/latest?from=USD&to=PHP"
    for attempt in range(1, settings.max_retries + 1):
        try:
            resp = requests.get(url, timeout=settings.request_timeout)
            resp.raise_for_status()
            data = resp.json()
            rate_val  = data["rates"]["PHP"]
            rate_date = date.fromisoformat(data["date"])
            return FXRate(
                rate_date=rate_date,
                currency_pair="USD/PHP",
                rate=round(rate_val, 4),
                source="frankfurter",
            )
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.warning("Frankfurter attempt %d/%d: %s", attempt, settings.max_retries, e)
            if attempt < settings.max_retries:
                time.sleep(2 ** attempt)
    return None


def fetch_historical(start_date: date, end_date: date) -> List[FXRate]:
    """
    Fetch historical USD/PHP rates from Frankfurter for a date range.
    Useful as a full historical backfill when BSP data is unavailable.
    """
    url = (
        f"{settings.fallback_api}/{start_date}..{end_date}"
        f"?from=USD&to=PHP"
    )
    records: List[FXRate] = []
    try:
        resp = requests.get(url, timeout=settings.request_timeout)
        resp.raise_for_status()
        data = resp.json()
        for date_str, rates in data.get("rates", {}).items():
            php_rate = rates.get("PHP")
            if php_rate:
                records.append(FXRate(
                    rate_date=date.fromisoformat(date_str),
                    currency_pair="USD/PHP",
                    rate=round(float(php_rate), 4),
                    source="frankfurter",
                ))
        logger.info("Frankfurter historical: fetched %d records.", len(records))
    except (requests.RequestException, ValueError) as e:
        logger.error("Frankfurter historical fetch failed: %s", e)
    return records
