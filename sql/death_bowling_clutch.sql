WITH death_overs_bowling AS (
    SELECT
        bowler,
        match_id,
        runs_total,
        runs_batter,
        is_wide,
        is_noball,
        is_wicket,
        dismissal_kind
    FROM deliveries
    WHERE over_num >= 15
      AND match_type = 'T20'
),
bowler_aggregates AS (
    SELECT
        bowler,
        COUNT(DISTINCT match_id) AS matches_bowled_in_death,
        SUM(runs_total) AS total_runs_conceded,
        COUNT(CASE WHEN is_wide = FALSE AND is_noball = FALSE THEN 1 END) AS legal_balls_bowled,
        SUM(CASE WHEN runs_batter = 0 AND is_wide = FALSE AND is_noball = FALSE THEN 1 ELSE 0 END) AS dot_balls,
        SUM(CASE WHEN is_wicket = TRUE AND dismissal_kind NOT IN ('run out', 'retired hurt') THEN 1 ELSE 0 END) AS wickets_taken
    FROM death_overs_bowling
    GROUP BY bowler
    HAVING COUNT(CASE WHEN is_wide = FALSE AND is_noball = FALSE THEN 1 END) >= 60
)
SELECT
    bowler,
    matches_bowled_in_death,
    legal_balls_bowled / 6 AS overs_bowled,
    total_runs_conceded,
    wickets_taken,
    ROUND((total_runs_conceded * 6.0 / NULLIF(legal_balls_bowled, 0)), 2) AS death_economy_rate,
    ROUND((dot_balls * 100.0 / NULLIF(legal_balls_bowled, 0)), 2) AS death_dot_ball_pct,
    DENSE_RANK() OVER (ORDER BY (total_runs_conceded * 6.0 / NULLIF(legal_balls_bowled, 0)) ASC) AS economy_rank
FROM bowler_aggregates
ORDER BY death_economy_rate ASC;
