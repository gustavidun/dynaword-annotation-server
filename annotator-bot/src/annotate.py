import logging
import time
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

from datasets import Dataset
from huggingface_hub import hf_hub_download, snapshot_download

from propella_bekko.inference import Annotator
from propella_bekko.models import PropellaBekko

from src.config import MODEL, HF_TOKEN

logger = logging.getLogger(__name__)
model, tok, cfg = PropellaBekko.load(snapshot_download(repo_id=MODEL))
ann = Annotator(model, tok, cfg["max_length"], cfg["tail_tokens"], device="cuda", max_tokens=262144)

def annotate_documents(docs : list[dict],annotator=ann) -> list[dict]:
    preds = annotator.annotate(docs)
    return preds

def annotate_dataset(
    repo_id: str,
    remote_path: str,
    local_path: Path,
    dataset_name: str,
    revision: str | None = None,
    hf_token: str = HF_TOKEN,
):
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

    num_shards = 10
    ds_shards = [ds.shard(num_shards=num_shards, index=i) for i in range(num_shards)]

    completed = 0
    t_start = time.monotonic()

    writer = None
    try:
        for i, shard in enumerate(ds_shards):
            rows = shard.to_pylist()
            preds = annotate_documents(rows)
            table = pa.Table.from_pylist([{"dataset": r["dataset"], "id": r["id"], **p} for r, p in zip(rows, preds, strict=True)])
            if writer is None:
                writer = pq.ParquetWriter(dest, table.schema)
            writer.write_table(table)
    
            completed += len(rows)
            elapsed = time.monotonic() - t_start
            pct = round((i+1)*(100/num_shards))
            docs_per_min = completed / elapsed * 60 if elapsed > 0 else 0
            remaining = (total - completed) / completed * elapsed if completed > 0 else 0

            prog_info = {
                "completed": completed,
                "total": total,
                "percent": pct,
                "docs_per_min": round(docs_per_min, 1),
                "eta_min": round(remaining / 60, 1),
            }
            if i == num_shards - 1:
                prog_info.update({"dest": dest})

            yield prog_info

    finally:
        if writer:
            writer.close()


