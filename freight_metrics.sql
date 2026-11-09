-- Freight performance metrics (PostgreSQL syntax)
-- Source tables mirror the CSVs in data/raw/:
--   shipments(shipment_id, month, origin, destination, miles, carrier, mode, weight_lbs,
--             freight_cost, on_time, days_late, transit_days, damaged)
--   fleet(month, truck_id, utilization, miles_driven, mpg, maintenance_cost)
-- `month` is stored as text 'YYYY-MM'.

-- 1. Monthly KPIs
SELECT
    s.month,
    COUNT(*)                                           AS shipments,
    ROUND(100.0 * AVG(s.on_time), 1)                   AS on_time_pct,
    ROUND(SUM(s.freight_cost))                         AS freight_cost,
    ROUND(SUM(s.freight_cost) / SUM(s.miles), 2)       AS cost_per_mile,
    ROUND(AVG(s.transit_days), 2)                      AS avg_transit_days,
    ROUND(100.0 * AVG(s.damaged), 2)                   AS damage_rate_pct
FROM shipments s
GROUP BY s.month
ORDER BY s.month;

-- 2. Fleet utilization by month
SELECT
    month,
    ROUND(100 * AVG(utilization), 1)  AS fleet_utilization_pct,
    ROUND(AVG(mpg), 2)                AS avg_mpg,
    ROUND(SUM(maintenance_cost))      AS maintenance_cost
FROM fleet
GROUP BY month
ORDER BY month;

-- 3. Carrier scorecard (last 12 months), flagged against a 95% on-time target
SELECT
    carrier,
    COUNT(*)                                                     AS shipments,
    ROUND(100.0 * AVG(on_time), 2)                               AS on_time_pct,
    ROUND(SUM(freight_cost) / SUM(miles), 2)                     AS cost_per_mile,
    ROUND(100.0 * AVG(damaged), 2)                               AS damage_rate_pct,
    ROUND(AVG(days_late) FILTER (WHERE on_time = 0), 2)          AS avg_days_late_when_late,
    CASE WHEN AVG(on_time) < 0.95 THEN 'Below target' ELSE 'On target' END AS status
FROM shipments
GROUP BY carrier
ORDER BY on_time_pct DESC;

-- 4. Lane performance
SELECT
    origin || ' -> ' || destination            AS lane,
    MAX(miles)                                 AS miles,
    COUNT(*)                                   AS shipments,
    ROUND(SUM(freight_cost))                   AS freight_cost,
    ROUND(100.0 * AVG(on_time), 1)             AS on_time_pct,
    ROUND(AVG(transit_days), 1)                AS avg_transit_days
FROM shipments
GROUP BY origin, destination
ORDER BY shipments DESC;

-- 5. Cost per mile by mode, with share of shipments (window function)
SELECT
    mode,
    COUNT(*)                                                    AS shipments,
    ROUND(SUM(freight_cost) / SUM(miles), 2)                    AS cost_per_mile,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)          AS share_pct
FROM shipments
GROUP BY mode
ORDER BY shipments DESC;

-- 6. Headline: last 3 months vs prior 3 months
WITH periods AS (
    SELECT *,
           CASE WHEN month IN ('2026-08','2026-09','2026-10') THEN 'current'
                WHEN month IN ('2026-05','2026-06','2026-07') THEN 'prior' END AS period
    FROM shipments
),
agg AS (
    SELECT period,
           COUNT(*)                                AS shipments,
           100.0 * AVG(on_time)                    AS on_time_pct,
           SUM(freight_cost) / SUM(miles)          AS cost_per_mile
    FROM periods
    WHERE period IS NOT NULL
    GROUP BY period
)
SELECT
    c.shipments,
    ROUND(100.0 * (c.shipments::numeric / p.shipments - 1), 1)        AS shipments_chg_pct,
    ROUND(c.on_time_pct, 1)                                           AS on_time_pct,
    ROUND(c.on_time_pct - p.on_time_pct, 1)                           AS on_time_chg_pts,
    ROUND(c.cost_per_mile, 2)                                         AS cost_per_mile,
    ROUND(100.0 * (c.cost_per_mile / p.cost_per_mile - 1), 1)         AS cost_per_mile_chg_pct
FROM agg c CROSS JOIN agg p
WHERE c.period = 'current' AND p.period = 'prior';
