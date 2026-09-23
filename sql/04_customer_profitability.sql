-- 04_customer_profitability.sql
-- FY2025 customer profitability after cost-to-serve, EUR.
-- Cost-to-serve = freight (driven by deliveries) + order handling (driven by orders:
-- changeovers, set-up waste, planning). Fixed costs are allocated on tonnes.
-- Sorted from most to least profitable, with the cumulative share of total EBITDA
-- (the "whale curve"): where the curve peaks above 100%, the tail is destroying value.

WITH s AS (
    SELECT f.*, g.other_var_eur_t
    FROM fact_sales f JOIN dim_segment g USING (segment_id)
    WHERE f.month LIKE '2025-%'
),
c AS (SELECT * FROM fact_plant_cost WHERE month LIKE '2025-%'),
plant_rate AS (
    SELECT c.plant_id,
           SUM(c.fibre_cost_eur)  / v.vol     AS fibre_t,
           SUM(c.energy_cost_eur) / v.vol     AS energy_t,
           SUM(c.other_variable_eur) / v.ov_std AS ov_scale
    FROM c
    JOIN (SELECT plant_id, SUM(volume_t) AS vol, SUM(volume_t * other_var_eur_t) AS ov_std
          FROM s GROUP BY plant_id) v USING (plant_id)
    GROUP BY c.plant_id
),
fixed AS (SELECT SUM(fixed_cost_eur) AS fixed25 FROM c),
cust AS (
    SELECT s.customer_id,
           SUM(s.volume_t)                                           AS volume_t,
           SUM(s.orders)                                             AS orders,
           SUM(s.net_sales_eur)                                      AS sales,
           SUM(s.volume_t * (r.fibre_t + r.energy_t + s.other_var_eur_t * r.ov_scale)) AS variable_cost,
           SUM(s.freight_eur + s.order_handling_eur)                 AS cost_to_serve
    FROM s JOIN plant_rate r USING (plant_id)
    GROUP BY s.customer_id
),
prof AS (
    SELECT cust.*,
           sales - variable_cost - cost_to_serve                     AS contribution_after_cts,
           sales - variable_cost - cost_to_serve
             - fixed.fixed25 * volume_t / SUM(volume_t) OVER ()      AS ebitda
    FROM cust, fixed
)
SELECT p.customer_id, d.tier, d.contract_type,
       ROUND(p.volume_t, 0)                          AS volume_t,
       ROUND(p.volume_t / p.orders, 1)               AS avg_order_t,
       ROUND(p.cost_to_serve / p.volume_t, 1)        AS cts_per_t,
       ROUND(p.contribution_after_cts / 1e6, 3)      AS contribution_after_cts_m,
       ROUND(p.ebitda / 1e6, 3)                      AS ebitda_m,
       ROUND(p.ebitda / p.sales * 100, 1)            AS ebitda_margin_pct,
       ROUND(SUM(p.ebitda) OVER (ORDER BY p.ebitda DESC ROWS UNBOUNDED PRECEDING)
             / SUM(p.ebitda) OVER () * 100, 1)       AS cumulative_ebitda_pct
FROM prof p JOIN dim_customer d USING (customer_id)
ORDER BY p.ebitda DESC;
