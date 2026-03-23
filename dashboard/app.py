"""
Philippine FX Dashboard — Streamlit app.

Reads from PostgreSQL mart tables:
  marts.fx_dashboard        — KPIs + daily rate + rolling averages
  marts.fx_volatility       — rolling std dev + vol regime
  marts.real_exchange_rate  — nominal vs CPI-adjusted rate
  raw.cross_rates           — latest cross rates vs PHP

Run locally:
  streamlit run dashboard/app.py

Run via Docker:
  docker compose up streamlit
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="PH FX Dashboard",
    page_icon="🇵🇭",
    layout="wide",
    initial_sidebar_state="expanded",
)

DSN = os.environ.get(
    "PH_FX_POSTGRES_DSN",
    "postgresql://fx:fx@localhost:5432/ph_fx",
)

ALERT_THRESHOLD = float(os.environ.get("PH_FX_ALERT_THRESHOLD_PCT", "1.5"))


@st.cache_data(ttl=300)
def load_fx_dashboard() -> pd.DataFrame:
    with psycopg2.connect(DSN) as conn:
        return pd.read_sql(
            "SELECT * FROM marts.fx_dashboard ORDER BY rate_date",
            conn, parse_dates=["rate_date"],
        )


@st.cache_data(ttl=300)
def load_volatility() -> pd.DataFrame:
    with psycopg2.connect(DSN) as conn:
        return pd.read_sql(
            "SELECT * FROM marts.fx_volatility ORDER BY rate_date",
            conn, parse_dates=["rate_date"],
        )


@st.cache_data(ttl=300)
def load_real_rate() -> pd.DataFrame:
    with psycopg2.connect(DSN) as conn:
        return pd.read_sql(
            "SELECT * FROM marts.real_exchange_rate ORDER BY month",
            conn, parse_dates=["month"],
        )


@st.cache_data(ttl=300)
def load_cross_rates() -> pd.DataFrame:
    with psycopg2.connect(DSN) as conn:
        return pd.read_sql(
            """SELECT base_currency, php_rate, rate_date
               FROM raw.cross_rates
               WHERE rate_date = (SELECT MAX(rate_date) FROM raw.cross_rates)
               ORDER BY base_currency""",
            conn, parse_dates=["rate_date"],
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🇵🇭 PH FX Dashboard")
st.sidebar.caption("Source: Bangko Sentral ng Pilipinas · Frankfurter API")

year_range = st.sidebar.slider(
    "Year range",
    min_value=2017, max_value=date.today().year,
    value=(2020, date.today().year),
)
alert_threshold = st.sidebar.number_input(
    "Alert threshold (%)", min_value=0.1, max_value=10.0,
    value=ALERT_THRESHOLD, step=0.1,
    help="Alert fires when daily move exceeds this percentage",
)
show_real_rate = st.sidebar.checkbox("Show real exchange rate overlay", value=True)

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    df      = load_fx_dashboard()
    vol_df  = load_volatility()
    real_df = load_real_rate()
    cross_df = load_cross_rates()
    db_ok = True
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# ── Filter by year range ──────────────────────────────────────────────────────
mask = (df["rate_date"].dt.year >= year_range[0]) & \
       (df["rate_date"].dt.year <= year_range[1])
df_f    = df[mask]
vol_f   = vol_df[vol_df["rate_date"].dt.year.between(*year_range)]

# ── Alert banner ──────────────────────────────────────────────────────────────
latest = df.iloc[-1] if not df.empty else None
if latest is not None and latest["daily_change_pct"] is not None:
    change = float(latest["daily_change_pct"])
    if abs(change) >= alert_threshold:
        direction = "weakened 📉" if change > 0 else "strengthened 📈"
        st.error(
            f"⚠️ **ALERT** — Peso {direction} by **{abs(change):.2f}%** today "
            f"(₱{latest['rate']:.4f})"
        )
    else:
        st.success(f"✅ No alert. Daily move: {change:+.2f}%")

# ── Metric cards ──────────────────────────────────────────────────────────────
st.markdown("### USD / PHP — Key Metrics")
c1, c2, c3, c4, c5 = st.columns(5)

if latest is not None:
    c1.metric("Current rate",    f"₱{latest['rate']:.4f}",
              f"{latest['daily_change_pct']:+.2f}%" if latest['daily_change_pct'] else None)
    c2.metric("30-day avg",      f"₱{latest['avg_30d']:.4f}")
    c3.metric("YTD low",         f"₱{latest['ytd_low']:.4f}")
    c4.metric("YTD high",        f"₱{latest['ytd_high']:.4f}")
    c5.metric("30d change",
              f"{latest['change_30d_pct']:+.2f}%" if latest['change_30d_pct'] else "—")

st.divider()

# ── Main chart: rate + rolling avg ────────────────────────────────────────────
st.markdown("### USD/PHP Rate Trend")
fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(go.Scatter(
    x=df_f["rate_date"], y=df_f["rate"],
    name="Daily rate", line=dict(color="#4c8ed4", width=1.5),
    fill="tozeroy", fillcolor="rgba(76,142,212,0.07)",
), secondary_y=False)

fig.add_trace(go.Scatter(
    x=df_f["rate_date"], y=df_f["avg_30d"],
    name="30-day avg", line=dict(color="#e09932", width=1.8, dash="dash"),
), secondary_y=False)

if show_real_rate and not real_df.empty:
    real_f = real_df[real_df["month"].dt.year.between(*year_range)]
    fig.add_trace(go.Scatter(
        x=real_f["month"], y=real_f["real_rate"],
        name="Real rate (CPI-adj)", line=dict(color="#3da679", width=1.5, dash="dot"),
    ), secondary_y=False)

# Volatility on secondary axis
fig.add_trace(go.Bar(
    x=vol_f["rate_date"], y=vol_f["vol_30d"],
    name="30d volatility", marker_color="rgba(216,90,48,0.25)",
), secondary_y=True)

fig.update_layout(
    height=400, hovermode="x unified",
    legend=dict(orientation="h", y=-0.15),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
fig.update_yaxes(title_text="PHP per 1 USD", secondary_y=False)
fig.update_yaxes(title_text="Volatility (std dev)", secondary_y=True)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Cross rates + SME margin calculator ───────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### Cross Rates vs PHP")
    if not cross_df.empty:
        cross_display = cross_df.rename(columns={
            "base_currency": "Currency",
            "php_rate": "PHP per 1 unit",
            "rate_date": "As of",
        })
        st.dataframe(cross_display, use_container_width=True, hide_index=True)
    else:
        st.info("No cross rate data available.")

with col_right:
    st.markdown("### 💱 SME Export Margin Calculator")
    st.caption("How much is your USD contract worth in pesos?")

    usd_amount = st.number_input(
        "Contract value (USD)", min_value=100.0,
        value=10_000.0, step=500.0, format="%.2f",
    )
    if latest is not None:
        current_php = usd_amount * float(latest["rate"])
        avg30_php   = usd_amount * float(latest["avg_30d"])
        ytd_low_php = usd_amount * float(latest["ytd_low"])
        ytd_hi_php  = usd_amount * float(latest["ytd_high"])

        st.metric("At current rate",   f"₱{current_php:,.2f}")
        st.metric("At 30-day avg",     f"₱{avg30_php:,.2f}",
                  f"{current_php - avg30_php:+,.2f} vs current")
        st.metric("At YTD best rate",  f"₱{ytd_low_php:,.2f}")
        st.metric("At YTD worst rate", f"₱{ytd_hi_php:,.2f}",
                  f"₱{ytd_hi_php - ytd_low_php:,.2f} swing this year")

st.divider()
st.caption(
    "Data: Bangko Sentral ng Pilipinas (bsp.gov.ph) · "
    "Frankfurter API (api.frankfurter.app) · "
    "PSA OpenSTAT (openstat.psa.gov.ph)"
)
