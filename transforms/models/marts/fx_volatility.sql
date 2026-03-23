-- fx_volatility: 30-day rolling standard deviation + annualized volatility
-- Used for volatility chart and alert threshold comparison

WITH daily AS (
    SELECT rate_date, rate
    FROM {{ ref('stg_fx_rates') }}
),

with_vol AS (
    SELECT
        rate_date,
        rate,

        -- 30-day rolling std dev (population)
        STDDEV_POP(rate) OVER (
            ORDER BY rate_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS vol_30d,

        -- 7-day rolling std dev (short-term spike detection)
        STDDEV_POP(rate) OVER (
            ORDER BY rate_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS vol_7d,

        -- Daily log return
        LN(rate / NULLIF(LAG(rate) OVER (ORDER BY rate_date), 0)) AS log_return
    FROM daily
)

SELECT
    rate_date,
    ROUND(rate::NUMERIC, 4)     AS rate,
    ROUND(vol_30d::NUMERIC, 6)  AS vol_30d,
    ROUND(vol_7d::NUMERIC, 6)   AS vol_7d,

    -- Annualized volatility (sqrt(252) for daily → annual)
    ROUND((vol_30d * SQRT(252))::NUMERIC, 6) AS annualized_vol,

    -- Volatility regime classification
    CASE
        WHEN vol_30d > 1.5 THEN 'high'
        WHEN vol_30d > 0.9 THEN 'moderate'
        ELSE 'low'
    END AS vol_regime,

    ROUND(log_return::NUMERIC, 6) AS log_return
FROM with_vol
ORDER BY rate_date
