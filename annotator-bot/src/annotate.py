import logging
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

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
    """Annotate a dataset concurrently, yielding progress after set percent increment.

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
    completed = 0
    last_yielded_pct = 0
    yield_interval = 1 if total > 10_000 else 10
    t_start = time.monotonic()

    batch_size = 5000
    current_batch = []
    
    writer = None
    buffer = {}
    next_write_idx = 0
    next_submit_idx = 0

    def flush_batch():
        nonlocal writer, current_batch
        if not current_batch:
            return
        table = pa.Table.from_pylist(current_batch)
        if writer is None:
            writer = pq.ParquetWriter(dest, table.schema)
        writer.write_table(table)
        current_batch.clear()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        pending = set()
        future_to_idx = {}
        
        def submit_more():
            nonlocal next_submit_idx
            # keep up to 2 * max_workers tasks in flight
            while len(pending) < max_workers * 2 and next_submit_idx < total:
                future = pool.submit(_process_one, next_submit_idx, ds[next_submit_idx])
                future_to_idx[future] = next_submit_idx
                pending.add(future)
                next_submit_idx += 1

        submit_more()

        try:
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    idx = future_to_idx.pop(future)
                    _, annotation = future.result()
                    
                    base = {col: ds[idx][col] for col in keep_cols if col in ds[idx]}
                    buffer[idx] = {**base, **annotation}
                    
                    while next_write_idx in buffer:
                        current_batch.append(buffer.pop(next_write_idx))
                        next_write_idx += 1
                        if len(current_batch) >= batch_size:
                            flush_batch()
                    
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
                
                submit_more()
        except Exception:
            if writer:
                writer.close()
            raise

    # flush any remaining items in the buffer
    while next_write_idx in buffer:
        current_batch.append(buffer.pop(next_write_idx))
        next_write_idx += 1
    flush_batch()
    
    if writer:
        writer.close()

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