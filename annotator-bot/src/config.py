from pathlib import Path
import yaml
import os
from dotenv import load_dotenv

ROOT = Path(__file__).parents[2]
load_dotenv(ROOT / ".env")

HF_TOKEN = os.environ.get("HF_TOKEN", "")

if HF_TOKEN == "":
    print("Warning: HF token not configured.")

CONFIG_NAME = os.environ.get("CONFIG_NAME", "config.yaml")
CONFIG_PATH = ROOT / CONFIG_NAME

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _cfg = yaml.safe_load(f) or {}

NAME: str = _cfg.get("name", "dynaword-bot")
INTERVAL_MINUTES: int = _cfg.get("interval_minutes", 5)
HF_REPO_IDS: list[str] = _cfg.get("hf_repo_ids", [""])
PARQUET_PATTERN: str = _cfg.get("parquet_pattern", "data/*/data.parquet")
MODEL: str = _cfg.get("model", "mradermacher/propella-1-4b-GGUF")

WEBHOOK_URL: str = _cfg.get("webhook_url", "https://dynaword-annotation-server.gustavidunsloth.workers.dev")
WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", "")

if WEBHOOK_SECRET == "":
    print("Warning: Webhook secret not configured.")