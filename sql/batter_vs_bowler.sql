WITH matchup_stats AS (
    SELECT
        batter,
        bowler,
        SUM(runs_batter) AS runs_scored,
        COUNT(CASE WHEN is_wide = FALSE THEN 1 END) AS balls_faced,
        SUM(CASE WHEN runs_batter = 0 AND is_wide = FALSE THEN 1 ELSE 0 END) AS dot_balls,
        SUM(CASE WHEN is_wicket = TRUE AND player_dismissed = batter THEN 1 ELSE 0 END) AS dismissals
    FROM deliveries
    GROUP BY batter, bowler
)
SELECT
    batter,
    bowler,
    runs_scored,
    balls_faced,
    dismissals,
    ROUND((runs_scored * 100.0 / NULLIF(balls_faced, 0)), 2) AS strike_rate,
    ROUND((dot_balls * 100.0 / NULLIF(balls_faced, 0)), 2) AS dot_ball_pct,
    ROUND((runs_scored * 1.0 / NULLIF(dismissals, 0)), 2) AS batting_avg_vs_bowler
FROM matchup_stats
WHERE balls_faced >= 18
ORDER BY balls_faced DESC, runs_scored DESC;
