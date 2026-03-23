-- real_exchange_rate: nominal USD/PHP adjusted for PH vs US CPI differential
-- Shows whether peso is genuinely weaker or just tracking inflation

WITH fx AS (
    SELECT
        DATE_TRUNC('month', rate_date)::DATE AS month,
        AVG(rate)                            AS avg_nominal_rate
    FROM {{ ref('stg_fx_rates') }}
    GROUP BY 1
),

cpi AS (
    SELECT
        DATE_TRUNC('month', period_date)::DATE AS month,
        cpi_index,
        inflation_pct
    FROM raw.cpi_monthly
    WHERE source = 'psa_openstat'
),

-- Base month anchor for index rebasing (use 2010-01-01)
base AS (
    SELECT avg_nominal_rate AS base_nominal
    FROM fx
    WHERE month = '2010-01-01'
    LIMIT 1
),

joined AS (
    SELECT
        f.month,
        f.avg_nominal_rate                              AS nominal_rate,
        c.cpi_index,
        c.inflation_pct,
        b.base_nominal
    FROM fx f
    LEFT JOIN cpi c USING (month)
    CROSS JOIN base b
    WHERE f.avg_nominal_rate IS NOT NULL
),

with_real AS (
    SELECT
        month,
        ROUND(nominal_rate::NUMERIC, 4)     AS nominal_rate,
        cpi_index,
        inflation_pct,

        -- Real exchange rate = nominal / (PH CPI / base CPI)
        -- A rising real rate = peso genuinely weakening beyond inflation
        CASE WHEN cpi_index > 0 AND base_nominal > 0
             THEN ROUND((nominal_rate / (cpi_index / 100.0))::NUMERIC, 4)
        END                                             AS real_rate,

        -- Overvaluation / undervaluation gap
        CASE WHEN cpi_index > 0 AND base_nominal > 0
             THEN ROUND((nominal_rate - (nominal_rate / (cpi_index / 100.0)))::NUMERIC, 4)
        END                                             AS inflation_gap
    FROM joined
)

SELECT
    month,
    nominal_rate,
    real_rate,
    inflation_gap,
    cpi_index,
    inflation_pct
FROM with_real
ORDER BY month
