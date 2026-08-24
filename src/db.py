import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass
from src.config import DB_PATH

@dataclass
class Command:
    timestamp: datetime
    command_name: str
    repo_id: str
    discussion_num: int


def get_last_sha(repo_id: str) -> str | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS repo_state (repo_id TEXT PRIMARY KEY, sha TEXT)")
        row = conn.execute("SELECT sha FROM repo_state WHERE repo_id = ?", (repo_id,)).fetchone()
        return row[0] if row else None


def save_last_sha(repo_id: str, sha: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS repo_state (repo_id TEXT PRIMARY KEY, sha TEXT)")
        conn.execute("INSERT OR REPLACE INTO repo_state VALUES (?, ?)", (repo_id, sha))

def log_command(command_name: str, repo_id: str, discussion_num: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS commands "
            "(timestamp TEXT, command_name TEXT, repo_id TEXT, discussion_num INTEGER)"
        )
        conn.execute(
            "INSERT INTO commands (timestamp, command_name, repo_id, discussion_num) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), command_name, repo_id, discussion_num)
        )

def get_commands(repo_id: str, threshold: datetime | None = None) -> list[Command]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE IF NOT EXISTS commands "
            "(timestamp TEXT, command_name TEXT, repo_id TEXT, discussion_num INTEGER)"
        )
        if threshold:
            rows = conn.execute(
                "SELECT * FROM commands WHERE repo_id = ? AND timestamp > ?",
                (repo_id, threshold.isoformat())
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM commands WHERE repo_id = ?",
                (repo_id,)
            ).fetchall()
        return [
            Command(
                timestamp=datetime.fromisoformat(row["timestamp"]).replace(tzinfo=timezone.utc),
                command_name=row["command_name"],
                repo_id=row["repo_id"],
                discussion_num=row["discussion_num"]
            )
            for row in rows
        ]

