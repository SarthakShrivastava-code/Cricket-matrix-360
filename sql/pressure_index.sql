WITH running_chase AS (
    SELECT
        d.match_id,
        d.over_num,
        d.ball_num,
        d.batter,
        d.runs_batter,
        d.runs_total,
        d.is_wide,
        d.is_noball,
        -- Running target total calculation
        SUM(d.runs_total) OVER (
            PARTITION BY d.match_id
            ORDER BY d.over_num, d.ball_num
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS current_chase_runs,
        -- Total target runs set in Innings 1
        m.target_runs
    FROM deliveries d
    JOIN (
        SELECT match_id, SUM(runs_total) + 1 AS target_runs
        FROM deliveries
        WHERE inning = 1
        GROUP BY match_id
    ) m ON d.match_id = m.match_id
    WHERE d.inning = 2
),
situational_deliveries AS (
    SELECT
        batter,
        runs_batter,
        is_wide,
        (target_runs - current_chase_runs) AS runs_required,
        (120 - ((over_num * 6) + ball_num)) AS balls_remaining,
        -- Required Run Rate per over
        ROUND(
            (target_runs - current_chase_runs) * 6.0 /
            NULLIF((120 - ((over_num * 6) + ball_num)), 0), 2
        ) AS current_rrr
    FROM running_chase
)
SELECT
    batter,
    COUNT(CASE WHEN is_wide = FALSE THEN 1 END) AS high_pressure_balls_faced,
    SUM(runs_batter) AS high_pressure_runs,
    ROUND((SUM(runs_batter) * 100.0 / NULLIF(COUNT(CASE WHEN is_wide = FALSE THEN 1 END), 0)), 2) AS pressure_strike_rate
FROM situational_deliveries
WHERE current_rrr >= 10.0 AND balls_remaining > 0
GROUP BY batter
HAVING COUNT(CASE WHEN is_wide = FALSE THEN 1 END) >= 20
ORDER BY pressure_strike_rate DESC;
