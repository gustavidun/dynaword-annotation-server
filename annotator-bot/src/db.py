import sqlite3
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from src.config import DB_PATH

import requests
from typing import Any
from src.config import WEBHOOK_URL, WEBHOOK_SECRET

@dataclass
class Command:
    timestamp: datetime
    command_name: str
    repo_id: str
    discussion_num: int

@dataclass
class Webhook:
    id: int
    payload: dict[str, Any]
    created_at: datetime
    status: str

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

def get_pending_webhooks() -> list[Webhook]:
    """Polls the Cloudflare Worker for up to 50 pending webhooks."""
    print(WEBHOOK_SECRET, WEBHOOK_URL)
    try:
        response = requests.get(WEBHOOK_URL, headers={"X-Webhook-Secret": WEBHOOK_SECRET})
        if response.status_code == 200:
            data = response.json()
            return [
                Webhook(
                    id=row["id"],
                    payload=json.loads(row["payload"]),
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                    status=row["status"]
                )
                for row in data
            ]
        else:
            print(f"Failed to fetch webhooks: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to worker: {e}")
        
    return []

def mark_webhooks_completed(ids: list[int]) -> bool:
    """Marks a list of webhook payload IDs as processed (completed)"""        
    try:
        response = requests.patch(
            WEBHOOK_URL, 
            headers={"X-Webhook-Secret": WEBHOOK_SECRET},
            json={"ids": ids}
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error updating webhooks: {e}")
        return False
