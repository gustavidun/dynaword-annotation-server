from pathlib import Path
import yaml

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config.yaml"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _cfg = yaml.safe_load(f) or {}

NAME: str = _cfg.get("name", "dynaword-bot")
INTERVAL_MINUTES: int = _cfg.get("interval_minutes", 5)
HF_REPO_ID: str = _cfg.get("hf_repo_id", "")
DB_PATH: str = _cfg.get("db_path", "state.db")
PARQUET_PATTERN: str = _cfg.get("parquet_pattern", "data/*/data.parquet")
MODEL: str = _cfg.get("model", "mradermacher/propella-1-4b-GGUF")
import os
from dotenv import load_dotenv

# Load the .env file from the root directory (one level up from annotator-bot)
load_dotenv(ROOT / ".env")

WEBHOOK_URL: str = _cfg.get("webhook_url", "https://dynaword-annotation-server.gustavidunsloth.workers.dev")
WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", "")

if WEBHOOK_SECRET == "":
    print("Warning: Webhook secret not configured.")