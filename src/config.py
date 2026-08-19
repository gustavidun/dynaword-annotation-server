from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]
CONFIG_PATH = ROOT / "config.yaml"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _cfg = yaml.safe_load(f) or {}

INTERVAL_MINUTES: int = _cfg.get("interval_minutes", 5)
HF_REPO_ID: str = _cfg.get("hf_repo_id", "gustavidunsloth/multilingual-dynaword-3")
DB_PATH: str = _cfg.get("db_path", "state.db")
PARQUET_PATTERN: str = _cfg.get("parquet_pattern", "data/*/data.parquet")
MODEL: str = _cfg.get("model", "mradermacher/propella-1-4b-GGUF")