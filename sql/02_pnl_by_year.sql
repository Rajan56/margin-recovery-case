-- 02_pnl_by_year.sql
-- Business unit P&L by year, EUR. The single source of truth every other view ties back to.

WITH s AS (
    SELECT CAST(substr(month, 1, 4) AS INTEGER) AS year,
           SUM(volume_t)            AS volume_t,
           SUM(net_sales_eur)       AS net_sales,
           SUM(freight_eur)         AS freight,
           SUM(order_handling_eur)  AS order_handling
    FROM fact_sales
    GROUP BY 1
),
c AS (
    SELECT CAST(substr(month, 1, 4) AS INTEGER) AS year,
           SUM(fibre_cost_eur)      AS fibre,
           SUM(energy_cost_eur)     AS energy,
           SUM(other_variable_eur)  AS other_variable,
           SUM(fixed_cost_eur)      AS fixed
    FROM fact_plant_cost
    GROUP BY 1
)
SELECT s.year,
       ROUND(s.volume_t, 0)                                         AS volume_t,
       ROUND(s.net_sales / 1e6, 2)                                  AS net_sales_m,
       ROUND((s.net_sales - c.fibre - c.energy - c.other_variable
              - s.freight - s.order_handling - c.fixed) / 1e6, 2)   AS ebitda_m,
       ROUND((s.net_sales - c.fibre - c.energy - c.other_variable
              - s.freight - s.order_handling - c.fixed)
             / s.net_sales * 100, 2)                                AS ebitda_margin_pct
FROM s JOIN c USING (year)
ORDER BY s.year;
