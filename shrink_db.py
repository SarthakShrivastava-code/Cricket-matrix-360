import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "cricket_matrix.db"
BACKUP_PATH = DB_PATH.with_name(
    f"{DB_PATH.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}{DB_PATH.suffix}"
)
REQUIRED_SUMMARIES = ("player_batting_summary", "player_bowling_summary")


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH, timeout=30)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing = set(REQUIRED_SUMMARIES) - tables
        if missing:
            raise RuntimeError(
                "Refusing to remove deliveries because summary tables are missing: "
                + ", ".join(sorted(missing))
            )

        summary_counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in REQUIRED_SUMMARIES
        }
        if any(count == 0 for count in summary_counts.values()):
            raise RuntimeError(
                f"Refusing to shrink an empty summary database: {summary_counts}"
            )

        if BACKUP_PATH.exists():
            raise FileExistsError(f"Backup already exists: {BACKUP_PATH}")

        print(f"Creating safety backup: {BACKUP_PATH}")
        backup = sqlite3.connect(BACKUP_PATH)
        try:
            connection.backup(backup)
        finally:
            backup.close()

        print("Dropping raw delivery tables...")
        connection.execute("DROP TABLE IF EXISTS deliveries")
        connection.execute("DROP TABLE IF EXISTS deliveries_backup")
        connection.commit()

        print("Vacuuming database to reclaim space...")
        connection.execute("VACUUM")

        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Shrunk database failed integrity check: {integrity}")
        remaining_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing = set(REQUIRED_SUMMARIES) - remaining_tables
        if missing:
            raise RuntimeError(
                "Summary tables missing after shrink: " + ", ".join(sorted(missing))
            )
        print(f"Summary rows retained: {summary_counts}")
    finally:
        connection.close()

    print(f"Compact database size: {DB_PATH.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"Original database backup: {BACKUP_PATH}")


if __name__ == "__main__":
    main()
