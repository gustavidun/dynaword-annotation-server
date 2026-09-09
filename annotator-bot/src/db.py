import json
from datetime import datetime
from dataclasses import dataclass

import requests
from typing import Any
from src.config import WEBHOOK_URL, WEBHOOK_SECRET

@dataclass
class Webhook:
    id: int
    payload: dict[str, Any]
    created_at: datetime
    status: str

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
