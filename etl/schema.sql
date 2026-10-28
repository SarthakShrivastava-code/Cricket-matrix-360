CREATE TABLE IF NOT EXISTS matches (
	match_id TEXT PRIMARY KEY,
	match_date TEXT,
	venue TEXT,
	city TEXT,
	team1 TEXT,
	team2 TEXT,
	toss_winner TEXT,
	toss_decision TEXT,
	match_type TEXT,
	competition_type TEXT,
	winner TEXT
);

CREATE TABLE IF NOT EXISTS deliveries (
	delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
	match_id TEXT NOT NULL,
	inning INTEGER NOT NULL,
	over_num INTEGER NOT NULL,
	ball_num INTEGER NOT NULL,
	batter TEXT NOT NULL,
	bowler TEXT NOT NULL,
	non_striker TEXT,
	batting_team TEXT,
	bowling_team TEXT,
	runs_batter INTEGER NOT NULL,
	runs_total INTEGER NOT NULL,
	is_wide BOOLEAN NOT NULL,
	is_noball BOOLEAN NOT NULL,
	is_wicket BOOLEAN NOT NULL,
	player_dismissed TEXT,
	dismissal_kind TEXT,
	bowler_style TEXT,
	FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE INDEX IF NOT EXISTS idx_deliveries_match
	ON deliveries(match_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_batter
	ON deliveries(batter);
CREATE INDEX IF NOT EXISTS idx_deliveries_bowler
	ON deliveries(bowler);
