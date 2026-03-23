"""
PostgreSQL upsert loader.
All inserts use ON CONFLICT DO UPDATE so re-running ingestion is always safe.
"""

from __future__ import annotations

import logging
from typing import Sequence

import psycopg2
import psycopg2.extras

from ph_fx.config import settings
from ph_fx.models import CPIRecord, CrossRate, FXRate

logger = logging.getLogger(__name__)

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.fx_daily (
    rate_date       DATE         NOT NULL,
    currency_pair   VARCHAR(10)  NOT NULL,
    rate            NUMERIC(12, 4) NOT NULL,
    source          VARCHAR(50)  NOT NULL,
    loaded_at       TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (rate_date, currency_pair)
);

CREATE TABLE IF NOT EXISTS raw.cross_rates (
    rate_date       DATE         NOT NULL,
    base_currency   CHAR(3)      NOT NULL,
    php_rate        NUMERIC(12, 4) NOT NULL,
    source          VARCHAR(50)  NOT NULL,
    loaded_at       TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (rate_date, base_currency)
);

CREATE TABLE IF NOT EXISTS raw.cpi_monthly (
    period_date     DATE         NOT NULL PRIMARY KEY,
    cpi_index       NUMERIC(10, 4) NOT NULL,
    inflation_pct   NUMERIC(8, 4),
    source          VARCHAR(50)  NOT NULL,
    loaded_at       TIMESTAMPTZ  DEFAULT NOW()
);
"""


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(settings.postgres_dsn)


def ensure_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
    logger.info("Schema ensured.")


def upsert_fx_rates(records: Sequence[FXRate]) -> int:
    if not records:
        return 0
    rows = [(r.rate_date, r.currency_pair, r.rate, r.source) for r in records]
    sql = """
        INSERT INTO raw.fx_daily (rate_date, currency_pair, rate, source)
        VALUES %s
        ON CONFLICT (rate_date, currency_pair)
        DO UPDATE SET rate = EXCLUDED.rate, source = EXCLUDED.source,
                      loaded_at = NOW()
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
        conn.commit()
    logger.info("Upserted %d FX rate records.", len(rows))
    return len(rows)


def upsert_cross_rates(records: Sequence[CrossRate]) -> int:
    if not records:
        return 0
    rows = [(r.rate_date, r.base_currency, r.php_rate, r.source) for r in records]
    sql = """
        INSERT INTO raw.cross_rates (rate_date, base_currency, php_rate, source)
        VALUES %s
        ON CONFLICT (rate_date, base_currency)
        DO UPDATE SET php_rate = EXCLUDED.php_rate, source = EXCLUDED.source,
                      loaded_at = NOW()
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
        conn.commit()
    logger.info("Upserted %d cross rate records.", len(rows))
    return len(rows)


def upsert_cpi(records: Sequence[CPIRecord]) -> int:
    if not records:
        return 0
    rows = [(r.period_date, r.cpi_index, r.inflation_pct, r.source) for r in records]
    sql = """
        INSERT INTO raw.cpi_monthly (period_date, cpi_index, inflation_pct, source)
        VALUES %s
        ON CONFLICT (period_date)
        DO UPDATE SET cpi_index = EXCLUDED.cpi_index,
                      inflation_pct = EXCLUDED.inflation_pct,
                      loaded_at = NOW()
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
        conn.commit()
    logger.info("Upserted %d CPI records.", len(rows))
    return len(rows)


def row_counts() -> dict[str, int]:
    tables = ["raw.fx_daily", "raw.cross_rates", "raw.cpi_monthly"]
    counts = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
    return counts
