-- views.sql — analytical views using window functions

-- 7-day rolling average temperature (168 hourly rows = 7 days)
CREATE VIEW IF NOT EXISTS rolling_avg_temp AS
SELECT
    city_id,
    observed_at,
    temperature_c,
    AVG(temperature_c) OVER (
        PARTITION BY city_id
        ORDER BY observed_at
        ROWS BETWEEN 167 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg
FROM weather_readings;

-- Day-over-day temperature delta (current vs 24 hours prior)
CREATE VIEW IF NOT EXISTS daily_delta AS
SELECT
    city_id,
    observed_at,
    temperature_c,
    temperature_c - LAG(temperature_c, 24) OVER (
        PARTITION BY city_id ORDER BY observed_at
    ) AS delta_24h
FROM weather_readings;

-- Z-score anomaly detection: readings >2.5 std devs from 30-day city mean
CREATE VIEW IF NOT EXISTS anomalies AS
WITH stats AS (
    SELECT
        city_id,
        AVG(temperature_c) AS mean_temp,
        -- variance = E[x²] - E[x]²  (avoids two-pass)
        AVG(temperature_c * temperature_c) - AVG(temperature_c) * AVG(temperature_c) AS variance
    FROM weather_readings
    WHERE observed_at >= datetime('now', '-30 days')
      AND temperature_c IS NOT NULL
    GROUP BY city_id
)
SELECT
    w.city_id,
    w.observed_at,
    w.temperature_c,
    s.mean_temp,
    SQRT(s.variance)                                                          AS std_dev,
    (w.temperature_c - s.mean_temp) / NULLIF(SQRT(s.variance), 0)            AS z_score
FROM weather_readings w
JOIN stats s ON w.city_id = s.city_id
WHERE
    w.temperature_c IS NOT NULL
    AND ABS((w.temperature_c - s.mean_temp) / NULLIF(SQRT(s.variance), 0)) > 2.5
ORDER BY ABS((w.temperature_c - s.mean_temp) / NULLIF(SQRT(s.variance), 0)) DESC;

-- City temperature rankings (latest reading per city)
CREATE VIEW IF NOT EXISTS city_latest AS
SELECT
    c.city_id,
    c.name,
    c.country,
    w.observed_at,
    w.temperature_c,
    w.humidity_pct,
    w.precipitation_mm,
    w.wind_speed_kmh,
    RANK() OVER (ORDER BY w.temperature_c DESC) AS temp_rank_hottest
FROM cities c
JOIN weather_readings w ON w.reading_id = (
    SELECT reading_id FROM weather_readings
    WHERE city_id = c.city_id
    ORDER BY observed_at DESC
    LIMIT 1
);
