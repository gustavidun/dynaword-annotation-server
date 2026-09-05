from pathlib import Path
import yaml
import os
from dotenv import load_dotenv

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config.yaml"

load_dotenv(ROOT / ".env")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _cfg = yaml.safe_load(f) or {}

NAME: str = _cfg.get("name", "dynaword-bot")
INTERVAL_MINUTES: int = _cfg.get("interval_minutes", 5)
HF_REPO_IDS: list[str] = _cfg.get("hf_repo_ids", [""])
DB_PATH: str = _cfg.get("db_path", "state.db")
PARQUET_PATTERN: str = _cfg.get("parquet_pattern", "data/*/data.parquet")
MODEL: str = _cfg.get("model", "mradermacher/propella-1-4b-GGUF")

WEBHOOK_URL: str = _cfg.get("webhook_url", "https://dynaword-annotation-server.gustavidunsloth.workers.dev")
WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", "")

if WEBHOOK_SECRET == "":
    print("Warning: Webhook secret not configured.")