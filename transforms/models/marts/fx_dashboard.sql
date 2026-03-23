-- fx_dashboard: KPIs + rolling averages + YTD stats
-- Primary source for Streamlit metric cards and main chart

WITH daily AS (
    SELECT
        rate_date,
        rate,
        LAG(rate, 1)  OVER (ORDER BY rate_date) AS prev_day_rate,
        LAG(rate, 7)  OVER (ORDER BY rate_date) AS rate_7d_ago,
        LAG(rate, 30) OVER (ORDER BY rate_date) AS rate_30d_ago,
        LAG(rate, 90) OVER (ORDER BY rate_date) AS rate_90d_ago
    FROM {{ ref('stg_fx_rates') }}
),

with_rolling AS (
    SELECT
        rate_date,
        rate,
        prev_day_rate,

        -- Rolling averages
        AVG(rate) OVER (ORDER BY rate_date ROWS BETWEEN 6  PRECEDING AND CURRENT ROW) AS avg_7d,
        AVG(rate) OVER (ORDER BY rate_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS avg_30d,
        AVG(rate) OVER (ORDER BY rate_date ROWS BETWEEN 89 PRECEDING AND CURRENT ROW) AS avg_90d,

        -- YTD stats
        MIN(rate) OVER (PARTITION BY DATE_TRUNC('year', rate_date)) AS ytd_low,
        MAX(rate) OVER (PARTITION BY DATE_TRUNC('year', rate_date)) AS ytd_high,

        -- Daily change
        CASE WHEN prev_day_rate > 0
             THEN ROUND(((rate - prev_day_rate) / prev_day_rate * 100)::NUMERIC, 4)
        END AS daily_change_pct,

        -- Period-over-period
        CASE WHEN rate_7d_ago  > 0 THEN ROUND(((rate - rate_7d_ago)  / rate_7d_ago  * 100)::NUMERIC, 4) END AS change_7d_pct,
        CASE WHEN rate_30d_ago > 0 THEN ROUND(((rate - rate_30d_ago) / rate_30d_ago * 100)::NUMERIC, 4) END AS change_30d_pct,
        CASE WHEN rate_90d_ago > 0 THEN ROUND(((rate - rate_90d_ago) / rate_90d_ago * 100)::NUMERIC, 4) END AS change_90d_pct,

        EXTRACT(YEAR  FROM rate_date) AS year,
        EXTRACT(MONTH FROM rate_date) AS month
    FROM daily
)

SELECT
    rate_date,
    ROUND(rate::NUMERIC, 4)      AS rate,
    ROUND(avg_7d::NUMERIC, 4)    AS avg_7d,
    ROUND(avg_30d::NUMERIC, 4)   AS avg_30d,
    ROUND(avg_90d::NUMERIC, 4)   AS avg_90d,
    ROUND(ytd_low::NUMERIC, 4)   AS ytd_low,
    ROUND(ytd_high::NUMERIC, 4)  AS ytd_high,
    daily_change_pct,
    change_7d_pct,
    change_30d_pct,
    change_90d_pct,
    year::INT  AS year,
    month::INT AS month
FROM with_rolling
ORDER BY rate_date
