-- 05_energy_anomaly.sql
-- Weekly energy intensity (MWh per tonne) against each plant's own seasonal baseline.
-- Baseline: FY2024 intensity for the same week-of-year, smoothed over five weeks.
-- Alert rule: the four-week rolling deviation stays above +6% for three weeks in a row.
-- A monthly report blends a drift like this into the average for weeks; this catches it
-- about six weeks after it starts.

WITH w AS (
    SELECT plant_id, week_start,
           CAST(substr(week_start, 1, 4) AS INTEGER)                 AS yr,
           (CAST(strftime('%j', week_start) AS INTEGER) - 1) / 7 + 1 AS woy,
           energy_mwh / production_t                                 AS intensity
    FROM fact_energy_week
),
base_raw AS (
    SELECT plant_id, woy, AVG(intensity) AS b
    FROM w WHERE yr = 2024 GROUP BY plant_id, woy
),
base AS (
    SELECT plant_id, woy,
           AVG(b) OVER (PARTITION BY plant_id ORDER BY woy
                        ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) AS baseline
    FROM base_raw
),
dev AS (
    SELECT w.*, base.baseline,
           w.intensity / base.baseline - 1 AS dev
    FROM w LEFT JOIN base USING (plant_id, woy)
),
roll AS (
    SELECT dev.*,
           CASE WHEN COUNT(dev) OVER win = 4 THEN AVG(dev) OVER win END AS dev_4w
    FROM dev
    WINDOW win AS (PARTITION BY plant_id ORDER BY week_start ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
),
flag AS (
    SELECT roll.*,
           CASE WHEN dev_4w > 0.06
                 AND LAG(dev_4w, 1) OVER p > 0.06
                 AND LAG(dev_4w, 2) OVER p > 0.06 THEN 1 ELSE 0 END AS alert
    FROM roll
    WINDOW p AS (PARTITION BY plant_id ORDER BY week_start)
)
SELECT plant_id,
       MIN(week_start)                   AS first_alert_week,
       ROUND(MAX(dev_4w) * 100, 1)       AS peak_4w_deviation_pct
FROM flag
WHERE alert = 1 AND yr = 2025
GROUP BY plant_id
ORDER BY first_alert_week;
