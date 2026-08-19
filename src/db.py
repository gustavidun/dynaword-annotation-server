import sqlite3
from src.config import DB_PATH

def get_last_sha(repo_id: str) -> str | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS repo_state (repo_id TEXT PRIMARY KEY, sha TEXT)")
        row = conn.execute("SELECT sha FROM repo_state WHERE repo_id = ?", (repo_id,)).fetchone()
        return row[0] if row else None


def save_last_sha(repo_id: str, sha: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS repo_state (repo_id TEXT PRIMARY KEY, sha TEXT)")
        conn.execute("INSERT OR REPLACE INTO repo_state VALUES (?, ?)", (repo_id, sha))
