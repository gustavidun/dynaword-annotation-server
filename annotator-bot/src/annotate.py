import logging
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dynaword.annotations.propella import (
    create_messages,
    AnnotationResponse,
    get_annotation_response_schema,
)
from openai import OpenAI
from datasets import Dataset
from huggingface_hub import hf_hub_download
from src.config import MODEL, ROOT, HF_TOKEN

logger = logging.getLogger(__name__)

MAX_WORKERS = 250

try:
    client = OpenAI(base_url="http://sglang:8000/v1", api_key="EMPTY")
except Exception as err:
    print(f"Can't connect to server: {err}")
    raise err


def annotate_document(document: str) -> dict:
    """Send a single document to the model and return the parsed annotation dict."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=create_messages(document),
            response_format={
                "type": "json_schema",
                "json_schema": {
                "name": "AnnotationResponse",
                "schema": get_annotation_response_schema(flatten=True, compact_whitespace=True),
                "strict": True,
            },
            },
        )
    except Exception as err:
        print(f"Error annotating document: {err}")
        raise err

    response_content = response.choices[0].message.content
    result = AnnotationResponse.model_validate_json(response_content)
    return result.model_dump()


def _process_one(idx: int, row: dict) -> tuple[int, dict]:
    return idx, annotate_document(row["text"])


def annotate_dataset(
    repo_id: str,
    remote_path: str,
    local_path: Path,
    dataset_name: str,
    revision: str | None = None,
    hf_token: str = HF_TOKEN,
    max_workers: int = MAX_WORKERS,
) -> Generator[dict, None, None]:
    """Annotate a dataset concurrently, yielding progress after each sample.

    Yields:
        dict with keys: completed, total, percent, and (on the last sample) dest.
    """
    print(f"Running annotations on {repo_id} {revision} {remote_path}.")
    dest = local_path / "metadata.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)

    local_parquet = hf_hub_download(
        repo_id=repo_id,
        filename=remote_path,
        repo_type="dataset",
        revision=revision,
        force_download=True,
        token=hf_token or None,
    )

    ds = Dataset.from_parquet(local_parquet)
    ds = ds.add_column("dataset", [dataset_name] * len(ds))
    total = len(ds)

    keep_cols = {"id", "dataset"}
    results: list[dict | None] = [None] * total
    completed = 0
    last_yielded_pct = 0
    yield_interval = 1 if total > 500_000 else 10
    t_start = time.monotonic()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_process_one, idx, ds[idx]): idx
            for idx in range(total)
        }
        try:
            for future in as_completed(futures):
                idx = futures[future]
                _, annotation = future.result()
                base = {col: ds[idx][col] for col in keep_cols if col in ds[idx]}
                results[idx] = {**base, **annotation}
                completed += 1

                pct = round(completed / total * 100)
                if pct >= last_yielded_pct + yield_interval:
                    last_yielded_pct = pct // yield_interval * yield_interval
                    elapsed = time.monotonic() - t_start
                    docs_per_min = completed / elapsed * 60 if elapsed > 0 else 0
                    remaining = (total - completed) / completed * elapsed if completed > 0 else 0
                    yield {
                        "completed": completed,
                        "total": total,
                        "percent": pct,
                        "docs_per_min": round(docs_per_min, 1),
                        "eta_min": round(remaining / 60, 1),
                    }
        except Exception:
            raise

    metadata = Dataset.from_list(results)
    metadata.to_parquet(str(dest))
    elapsed = time.monotonic() - t_start
    docs_per_min = total / elapsed * 60 if elapsed > 0 else 0
    yield {
        "completed": total,
        "total": total,
        "percent": 100,
        "docs_per_min": round(docs_per_min, 1),
        "eta_min": 0,
        "dest": dest,
    }