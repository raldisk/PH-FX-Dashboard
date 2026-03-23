-- stg_fx_rates: clean, deduplicate, forward-fill gaps on non-trading days
-- Source: raw.fx_daily

WITH source AS (
    SELECT
        rate_date,
        currency_pair,
        rate,
        source,
        ROW_NUMBER() OVER (
            PARTITION BY rate_date, currency_pair
            ORDER BY loaded_at DESC
        ) AS rn
    FROM raw.fx_daily
    WHERE rate IS NOT NULL
      AND rate > 0
),

deduped AS (
    SELECT
        rate_date,
        currency_pair,
        rate,
        source
    FROM source
    WHERE rn = 1
),

-- Fill in weekend / holiday gaps with previous trading day's rate
date_spine AS (
    SELECT generate_series(
        (SELECT MIN(rate_date) FROM deduped),
        CURRENT_DATE,
        INTERVAL '1 day'
    )::DATE AS rate_date
),

filled AS (
    SELECT
        ds.rate_date,
        d.currency_pair,
        COALESCE(
            d.rate,
            LAST_VALUE(d.rate IGNORE NULLS) OVER (
                PARTITION BY d.currency_pair
                ORDER BY ds.rate_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS rate,
        COALESCE(d.source, 'forward_fill') AS source
    FROM date_spine ds
    LEFT JOIN deduped d ON ds.rate_date = d.rate_date
        AND d.currency_pair = 'USD/PHP'
    WHERE d.currency_pair IS NOT NULL
       OR ds.rate_date >= (SELECT MIN(rate_date) FROM deduped WHERE currency_pair = 'USD/PHP')
)

SELECT
    rate_date,
    'USD/PHP' AS currency_pair,
    rate,
    source
FROM filled
WHERE rate IS NOT NULL
ORDER BY rate_date
