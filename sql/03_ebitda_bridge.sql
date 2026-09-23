-- 03_ebitda_bridge.sql
-- EBITDA bridge FY2024 -> FY2025, EUR m, built at customer level.
--   Volume  = change in total tonnes x FY2024 average unit contribution
--   Mix     = shift in tonnes between customers with different FY2024 unit contribution
--   Price   = FY2025 tonnes x change in price per tonne, constant currency
--   Cost    = FY2025 tonnes x change in cost per tonne, constant currency
--   Fixed   = change in fixed costs, constant currency
--   FX      = everything the SEK move did when translating FY2025 into EUR
-- Constant currency: FY2025 SEK amounts restated at the same month's FY2024 rate.
-- The rows sum exactly to the reported EBITDA change.

WITH fx24 AS (
    SELECT substr(month, 6, 2) AS mm, sek_per_eur AS rate24
    FROM fact_fx WHERE month LIKE '2024-%'
),
s AS (                                   -- sales rows with constant-currency values
    SELECT f.*,
           CAST(substr(f.month, 1, 4) AS INTEGER) AS year,
           CASE WHEN f.currency = 'SEK' THEN f.net_sales_local / x.rate24 ELSE f.net_sales_eur END      AS sales_cc,
           CASE WHEN f.currency = 'SEK' THEN f.freight_local / x.rate24 ELSE f.freight_eur END          AS freight_cc,
           CASE WHEN f.currency = 'SEK' THEN f.order_handling_local / x.rate24 ELSE f.order_handling_eur END AS oh_cc,
           g.other_var_eur_t
    FROM fact_sales f
    JOIN fx24 x ON x.mm = substr(f.month, 6, 2)
    JOIN dim_segment g ON g.segment_id = f.segment_id
),
c AS (                                   -- plant costs with constant-currency values
    SELECT p.*,
           CAST(substr(p.month, 1, 4) AS INTEGER) AS year,
           CASE WHEN p.currency = 'SEK' THEN p.energy_cost_local / x.rate24 ELSE p.energy_cost_eur END AS energy_cc,
           CASE WHEN p.currency = 'SEK' THEN p.fixed_cost_local  / x.rate24 ELSE p.fixed_cost_eur  END AS fixed_cc
    FROM fact_plant_cost p
    JOIN fx24 x ON x.mm = substr(p.month, 6, 2)
),
plant_rate AS (                          -- plant cost per tonne, and the scale that ties
    SELECT c.plant_id, c.year,           -- segment standard rates to the plant ledger
           SUM(c.fibre_cost_eur) / v.vol  AS fibre_t,
           SUM(c.energy_cc)      / v.vol  AS energy_cc_t,
           SUM(c.other_variable_eur) / v.ov_std AS ov_scale
    FROM c
    JOIN (SELECT plant_id, year, SUM(volume_t) AS vol,
                 SUM(volume_t * other_var_eur_t) AS ov_std
          FROM s GROUP BY plant_id, year) v
      ON v.plant_id = c.plant_id AND v.year = c.year
    GROUP BY c.plant_id, c.year
),
cust_year AS (
    SELECT s.customer_id, s.year,
           SUM(s.volume_t)                                   AS vol,
           SUM(s.sales_cc)                                   AS sales_cc,
           SUM(s.volume_t * r.fibre_t)                       AS fibre,
           SUM(s.volume_t * r.energy_cc_t)                   AS energy_cc,
           SUM(s.volume_t * s.other_var_eur_t * r.ov_scale)  AS other_var,
           SUM(s.freight_cc + s.oh_cc)                       AS cts_cc
    FROM s JOIN plant_rate r ON r.plant_id = s.plant_id AND r.year = s.year
    GROUP BY s.customer_id, s.year
),
cy AS (                                  -- one row per customer, FY2024 and FY2025 side by side
    SELECT a.customer_id,
           a.vol AS v24, b.vol AS v25,
           a.sales_cc / a.vol AS p24,   b.sales_cc / b.vol AS p25,
           a.fibre / a.vol AS fib24,    b.fibre / b.vol AS fib25,
           a.energy_cc / a.vol AS en24, b.energy_cc / b.vol AS en25,
           a.other_var / a.vol AS ov24, b.other_var / b.vol AS ov25,
           a.cts_cc / a.vol AS cts24,   b.cts_cc / b.vol AS cts25,
           (a.sales_cc - a.fibre - a.energy_cc - a.other_var - a.cts_cc) / a.vol AS ucm24
    FROM cust_year a JOIN cust_year b
      ON b.customer_id = a.customer_id AND a.year = 2024 AND b.year = 2025
),
tot AS (
    SELECT SUM(v24) AS v24, SUM(v25) AS v25,
           SUM(v24 * ucm24) / SUM(v24) AS ucm24_avg
    FROM cy
),
fixed AS (
    SELECT SUM(CASE WHEN year = 2024 THEN fixed_cost_eur END) AS fixed24,
           SUM(CASE WHEN year = 2025 THEN fixed_cc END)       AS fixed25_cc
    FROM c
),
reported AS (                            -- reported FY2025 EBITDA in EUR
    SELECT (SELECT SUM(net_sales_eur - freight_eur - order_handling_eur)
            FROM fact_sales WHERE month LIKE '2025-%')
         - (SELECT SUM(fibre_cost_eur + energy_cost_eur + other_variable_eur + fixed_cost_eur)
            FROM fact_plant_cost WHERE month LIKE '2025-%') AS ebitda25
),
cc25 AS (                                -- FY2025 EBITDA at FY2024 rates
    SELECT SUM(v25 * (p25 - fib25 - en25 - ov25 - cts25)) - (SELECT fixed25_cc FROM fixed) AS ebitda25_cc
    FROM cy
),
bridge AS (
    SELECT 1 AS ord, 'Volume' AS driver, (tot.v25 - tot.v24) * tot.ucm24_avg AS value FROM tot
    UNION ALL SELECT 2, 'Mix', (SELECT SUM(v25 * ucm24) FROM cy) - tot.v25 * tot.ucm24_avg FROM tot
    UNION ALL SELECT 3, 'Price',          SUM(v25 * (p25 - p24))     FROM cy
    UNION ALL SELECT 4, 'Fibre cost',     -SUM(v25 * (fib25 - fib24)) FROM cy
    UNION ALL SELECT 5, 'Energy cost',    -SUM(v25 * (en25 - en24))   FROM cy
    UNION ALL SELECT 6, 'Cost-to-serve',  -SUM(v25 * (cts25 - cts24)) FROM cy
    UNION ALL SELECT 7, 'Other variable', -SUM(v25 * (ov25 - ov24))   FROM cy
    UNION ALL SELECT 8, 'Fixed costs',    -(fixed25_cc - fixed24)     FROM fixed
    UNION ALL SELECT 9, 'FX (SEK)',       reported.ebitda25 - cc25.ebitda25_cc FROM reported, cc25
)
SELECT driver, ROUND(value / 1e6, 2) AS value_m
FROM bridge
ORDER BY ord;
