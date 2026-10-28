import json
import sqlite3
from glob import glob
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "cricket_matrix.db"

SCHEMA = """
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
"""

INDEXES = [
    ("idx_deliveries_match", "CREATE INDEX IF NOT EXISTS idx_deliveries_match ON deliveries(match_id)"),
    ("idx_deliveries_batter", "CREATE INDEX IF NOT EXISTS idx_deliveries_batter ON deliveries(batter)"),
    ("idx_deliveries_bowler", "CREATE INDEX IF NOT EXISTS idx_deliveries_bowler ON deliveries(bowler)"),
]


def _first(value, default=None):
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def _ensure_columns(connection):
    columns = {row[1] for row in connection.execute("PRAGMA table_info(matches)")}
    if "competition_type" not in columns:
        connection.execute("ALTER TABLE matches ADD COLUMN competition_type TEXT")

    columns = {row[1] for row in connection.execute("PRAGMA table_info(deliveries)")}
    if "bowler_style" not in columns:
        connection.execute("ALTER TABLE deliveries ADD COLUMN bowler_style TEXT")


def _competition_type(info):
    match_type = info.get("match_type")
    event_name = str(info.get("event", {}).get("name", ""))
    if match_type == "T20" and "IPL" in event_name.upper():
        return "IPL"
    if match_type == "T20" and info.get("gender") and "international" in event_name.lower():
        return "T20I"
    return match_type


def _delivery_rows(match_id, match_info, innings):
    rows = []
    teams = match_info.get("teams", [])
    
    for inning_number, innings_data in enumerate(innings, start=1):
        batting_team = innings_data.get("team")
        bowling_team = next((team for team in teams if team != batting_team), None)
        
        for over in innings_data.get("overs", []):
            over_num = int(over.get("over", 0))
            for ball_index, delivery in enumerate(over.get("deliveries", [])):
                actual_delivery = str(delivery.get("actual_delivery", ""))
                ball_num = int(actual_delivery.split(".")[-1]) if "." in actual_delivery else ball_index + 1
                extras = delivery.get("extras", {})
                wickets = delivery.get("wickets", [])
                wicket = wickets[0] if wickets else {}
                runs = delivery.get("runs", {})
                
                rows.append(
                    (
                        match_id,
                        inning_number,
                        over_num,
                        ball_num,
                        delivery.get("batter"),
                        delivery.get("bowler"),
                        delivery.get("non_striker"),
                        batting_team,
                        bowling_team,
                        runs.get("batter", 0),
                        runs.get("total", 0),
                        int("wides" in extras),
                        int("noballs" in extras),
                        int(bool(wickets)),
                        wicket.get("player_out"),
                        wicket.get("kind"),
                        None,  # bowler_style default
                    )
                )
    return rows


def parse_match_json(json_file):
    with open(json_file, encoding="utf-8") as file:
        match = json.load(file)

    info = match.get("info", {})
    outcome = info.get("outcome", {})
    toss = info.get("toss", {})
    teams = info.get("teams", [])
    match_id = Path(json_file).stem
    
    match_row = (
        match_id,
        _first(info.get("dates")),
        info.get("venue"),
        info.get("city"),
        teams[0] if len(teams) > 0 else None,
        teams[1] if len(teams) > 1 else None,
        toss.get("winner"),
        toss.get("decision"),
        info.get("match_type"),
        _competition_type(info),  # Corrected positioning: competition_type
        outcome.get("winner"),     # Corrected positioning: winner
    )
    return match_row, _delivery_rows(match_id, info, match.get("innings", []))


def _set_sqlite_pragmas(connection):
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")


def run_etl_batched(json_folder_path, batch_size=1000, db_path=DEFAULT_DB_PATH):
    raw_path = Path(json_folder_path)
    if not raw_path.is_absolute():
        raw_path = BASE_DIR / raw_path
    db_path = Path(db_path)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    json_files = sorted(glob(str(raw_path / "*.json")))
    total_files = len(json_files)
    if not total_files:
        raise FileNotFoundError(f"No JSON files found in {raw_path}")
    print(f"Total files to process: {total_files}")

    connection = sqlite3.connect(db_path)
    try:
        _set_sqlite_pragmas(connection)
        connection.executescript(SCHEMA)
        _ensure_columns(connection)
        
        # Safely Drop Indexes
        for index_name, _ in INDEXES:
            connection.execute(f"DROP INDEX IF EXISTS {index_name}")
            
        connection.execute("DELETE FROM deliveries")
        connection.execute("DELETE FROM matches")

        # Corrected Column Mapping Order
        match_insert = """
            INSERT INTO matches (
                match_id, match_date, venue, city, team1, team2,
                toss_winner, toss_decision, match_type, competition_type, winner
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        delivery_insert = """
            INSERT INTO deliveries (
                match_id, inning, over_num, ball_num, batter, bowler,
                non_striker, batting_team, bowling_team, runs_batter,
                runs_total, is_wide, is_noball, is_wicket,
                player_dismissed, dismissal_kind, bowler_style
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        all_matches = []
        all_deliveries = []
        
        for idx, json_file in enumerate(json_files, start=1):
            try:
                match_row, delivery_rows = parse_match_json(json_file)
            except Exception:
                continue

            all_matches.append(match_row)
            all_deliveries.extend(delivery_rows)
            
            if idx % batch_size == 0 or idx == total_files:
                connection.executemany(match_insert, all_matches)
                connection.executemany(delivery_insert, all_deliveries)
                connection.commit()
                print(f"Processed & committed: {idx}/{total_files} files...")
                all_matches.clear()
                all_deliveries.clear()

        # Re-create Indexes
        for _, index_sql in INDEXES:
            connection.execute(index_sql)
            
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.commit()
    finally:
        connection.close()

    print(f"SUCCESS: Loaded data into {db_path}")


def run_etl(raw_folder="data/raw_jsons", db_path=DEFAULT_DB_PATH):
    run_etl_batched(raw_folder, db_path=db_path)


if __name__ == "__main__":
    run_etl("data/raw_jsons")