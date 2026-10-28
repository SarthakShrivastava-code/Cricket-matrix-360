WITH phase_deliveries AS (
    SELECT
        batter,
        CASE
            WHEN over_num BETWEEN 0 AND 5 THEN 'Powerplay (0-6)'
            WHEN over_num BETWEEN 6 AND 14 THEN 'Middle Overs (7-15)'
            WHEN over_num BETWEEN 15 AND 19 THEN 'Death Overs (16-20)'
        END AS match_phase,
        runs_batter,
        is_wide,
        CASE WHEN runs_batter = 0 AND is_wide = FALSE THEN 1 ELSE 0 END AS is_dot_ball,
        CASE WHEN runs_batter = 4 THEN 1 ELSE 0 END AS is_four,
        CASE WHEN runs_batter = 6 THEN 1 ELSE 0 END AS is_six
    FROM deliveries
    WHERE match_id IN (SELECT match_id FROM matches WHERE match_type = 'T20')
),
phase_summary AS (
    SELECT
        batter,
        match_phase,
        SUM(runs_batter) AS total_runs,
        COUNT(CASE WHEN is_wide = FALSE THEN 1 END) AS balls_faced,
        SUM(is_dot_ball) AS dot_balls,
        SUM(is_four) AS fours,
        SUM(is_six) AS sixes
    FROM phase_deliveries
    GROUP BY batter, match_phase
    HAVING COUNT(CASE WHEN is_wide = FALSE THEN 1 END) >= 30
)
SELECT
    batter,
    match_phase,
    total_runs,
    balls_faced,
    ROUND((total_runs * 100.0 / NULLIF(balls_faced, 0)), 2) AS strike_rate,
    ROUND((dot_balls * 100.0 / NULLIF(balls_faced, 0)), 2) AS dot_ball_pct,
    ROUND(((fours * 4 + sixes * 6) * 100.0 / NULLIF(total_runs, 0)), 2) AS boundary_run_pct,
    DENSE_RANK() OVER (
        PARTITION BY match_phase
        ORDER BY (total_runs * 100.0 / NULLIF(balls_faced, 0)) DESC
    ) AS phase_sr_rank
FROM phase_summary
ORDER BY match_phase, phase_sr_rank;
