"""
Volatility alert logic.
Fires when the USD/PHP rate moves more than threshold_pct in a single day.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import psycopg2

from ph_fx.config import settings
from ph_fx.loader import get_connection

logger = logging.getLogger(__name__)


@dataclass
class AlertResult:
    triggered: bool
    today_rate: Optional[float]
    yesterday_rate: Optional[float]
    change_pct: Optional[float]
    message: str


def check_daily_alert(threshold_pct: Optional[float] = None) -> AlertResult:
    """
    Compare today's USD/PHP rate against yesterday's.
    Returns AlertResult — triggered=True when abs(change) > threshold_pct.
    """
    threshold = threshold_pct or settings.alert_threshold_pct
    today = date.today()
    yesterday = today - timedelta(days=1)

    sql = """
        SELECT rate_date, rate
        FROM raw.fx_daily
        WHERE currency_pair = 'USD/PHP'
          AND rate_date IN (%s, %s)
        ORDER BY rate_date DESC
        LIMIT 2
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (today, yesterday))
                rows = cur.fetchall()
    except psycopg2.Error as e:
        logger.warning("Alert check failed: %s", e)
        return AlertResult(
            triggered=False, today_rate=None, yesterday_rate=None,
            change_pct=None, message="Could not fetch rates for alert check."
        )

    if len(rows) < 2:
        return AlertResult(
            triggered=False, today_rate=None, yesterday_rate=None,
            change_pct=None, message="Insufficient data for alert check."
        )

    today_rate     = float(rows[0][1])
    yesterday_rate = float(rows[1][1])
    change_pct     = ((today_rate - yesterday_rate) / yesterday_rate) * 100

    triggered = abs(change_pct) >= threshold
    direction = "weakened" if change_pct > 0 else "strengthened"
    message = (
        f"⚠️ ALERT: Peso {direction} by {abs(change_pct):.2f}% today "
        f"(₱{yesterday_rate:.4f} → ₱{today_rate:.4f})"
        if triggered
        else f"No alert. Daily move: {change_pct:+.2f}%"
    )

    return AlertResult(
        triggered=triggered,
        today_rate=today_rate,
        yesterday_rate=yesterday_rate,
        change_pct=round(change_pct, 4),
        message=message,
    )
