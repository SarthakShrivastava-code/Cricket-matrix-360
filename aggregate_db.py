import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
JSON_FOLDER = BASE_DIR / "data" / "raw_jsons"
DB_PATH = BASE_DIR / "data" / "cricket_matrix.db"
NAME_MAP = {
    "Virat Kohli": "V Kohli",
    "Rohit Sharma": "RG Sharma",
    "Suryakumar Yadav": "Suryakumar Yadav",
    "SK Yadav": "Suryakumar Yadav",
    "Jasprit Bumrah": "JJ Bumrah",
    "KL Rahul": "KL Rahul",
    "Hardik Pandya": "HH Pandya",
    "MS Dhoni": "MS Dhoni",
    "Ravindra Jadeja": "R Jadeja",
    "Bhuvaneshwar Kumar": "B Kumar",
}
ALLOWED_MATCH_TYPES = {"Test", "ODI", "T20I", "T20"}
EXCLUDED_EVENT_TERMS = ("league", "ipl", "bbl", "psl")
MIN_YEAR = 2000
MAX_YEAR = 2026
FILE_BATCH_SIZE = 1000


def clean_name(name):
    if not name:
        return name
    name = name.strip()
    return NAME_MAP.get(name, name)


def match_year(info):
    dates = info.get("dates") or []
    date_value = dates[0] if isinstance(dates, list) and dates else dates
    try:
        year = int(str(date_value)[:4])
    except (TypeError, ValueError):
        return None
    return year if MIN_YEAR <= year <= MAX_YEAR else None


def aggregate_match(file_path, batting, bowling):
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    info = data.get("info", {})
    match_type = info.get("match_type", "")
    if match_type not in ALLOWED_MATCH_TYPES:
        return False

    event = info.get("event") or {}
    event_name = event.get("name", "") if isinstance(event, dict) else str(event)
    if any(term in event_name.lower() for term in EXCLUDED_EVENT_TERMS):
        return False

    year = match_year(info)
    if year is None:
        return False

    for innings in data.get("innings", []):
        for over_item in innings.get("overs", []):
            over_num = over_item.get("over", 0)
            phase = "Powerplay" if over_num < 6 else "Middle" if over_num < 15 else "Death"
            for delivery in over_item.get("deliveries", []):
                batter = clean_name(delivery.get("batter"))
                bowler = clean_name(delivery.get("bowler"))
                runs = delivery.get("runs") or {}
                batter_runs = runs.get("batter", 0)
                total_runs = runs.get("total", 0)
                extras = delivery.get("extras") or {}
                is_wide = "wides" in extras
                is_noball = "noballs" in extras
                is_wicket = bool(delivery.get("wickets"))

                if batter is not None and not is_wide:
                    stats = batting[(batter, match_type, year, phase)]
                    stats[0] += batter_runs
                    stats[1] += 1
                    stats[2] += int(batter_runs == 4)
                    stats[3] += int(batter_runs == 6)
                    stats[4] += int(batter_runs == 0)
                    stats[5] += int(is_wicket)

                if bowler is not None:
                    stats = bowling[(bowler, match_type, year, phase)]
                    stats[0] += total_runs
                    stats[1] += int(not is_wide and not is_noball)
                    stats[2] += int(total_runs == 0)
                    stats[3] += int(is_wicket)
    return True


def replace_summary_tables(connection, batting, bowling):
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("""
            CREATE TABLE player_batting_summary_new (
                player TEXT, format TEXT, year INTEGER, phase TEXT,
                runs INTEGER, balls INTEGER, fours INTEGER, sixes INTEGER,
                dot INTEGER, dismissed INTEGER
            )
        """)
        connection.execute("""
            CREATE TABLE player_bowling_summary_new (
                player TEXT, format TEXT, year INTEGER, phase TEXT,
                runs_conceded INTEGER, balls_bowled INTEGER, dot INTEGER,
                wickets INTEGER
            )
        """)
        connection.executemany(
            "INSERT INTO player_batting_summary_new VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(*key, *values) for key, values in batting.items()],
        )
        connection.executemany(
            "INSERT INTO player_bowling_summary_new VALUES (?,?,?,?,?,?,?,?)",
            [(*key, *values) for key, values in bowling.items()],
        )
        connection.execute("DROP TABLE IF EXISTS player_batting_summary")
        connection.execute("DROP TABLE IF EXISTS player_bowling_summary")
        connection.execute(
            "ALTER TABLE player_batting_summary_new RENAME TO player_batting_summary"
        )
        connection.execute(
            "ALTER TABLE player_bowling_summary_new RENAME TO player_bowling_summary"
        )
        connection.execute(
            "CREATE INDEX idx_batting_summary_lookup "
            "ON player_batting_summary(player, format, year, phase)"
        )
        connection.execute(
            "CREATE INDEX idx_bowling_summary_lookup "
            "ON player_bowling_summary(player, format, year, phase)"
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def main():
    json_files = sorted(JSON_FOLDER.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON match files found in {JSON_FOLDER}")

    print(f"Reading {len(json_files):,} JSON match files (2000–2026)...")
    batting = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    bowling = defaultdict(lambda: [0, 0, 0, 0])
    included_matches = 0
    filtered_matches = 0
    invalid_files = 0
    invalid_examples = []

    for index, file_path in enumerate(json_files, start=1):
        try:
            included = aggregate_match(file_path, batting, bowling)
            if included:
                included_matches += 1
            else:
                filtered_matches += 1
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError) as error:
            invalid_files += 1
            if len(invalid_examples) < 5:
                invalid_examples.append(f"{file_path.name}: {error}")

        if index % FILE_BATCH_SIZE == 0:
            print(f"Processed {index:,}/{len(json_files):,} files...")

    if not batting or not bowling:
        raise RuntimeError("No batting or bowling aggregates were produced; database unchanged.")

    connection = sqlite3.connect(DB_PATH, timeout=30)
    try:
        replace_summary_tables(connection, batting, bowling)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Database integrity check failed after aggregation: {integrity}")
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()

    connection = sqlite3.connect(DB_PATH, timeout=30)
    try:
        connection.execute("VACUUM")
    finally:
        connection.close()

    print(f"Included {included_matches:,} matches; filtered {filtered_matches:,}.")
    print(f"Created {len(batting):,} batting and {len(bowling):,} bowling summary rows.")
    print(f"Skipped {invalid_files:,} unreadable or malformed files.")
    for example in invalid_examples:
        print(f"  {example}")
    print(
        f"Aggregated database size: "
        f"{DB_PATH.stat().st_size / (1024 * 1024):.2f} MB"
    )
    print(f"Completed at {datetime.now():%Y-%m-%d %H:%M:%S}.")


if __name__ == "__main__":
    main()
