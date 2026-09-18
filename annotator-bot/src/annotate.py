import asyncio
from pathlib import Path

from openai import AsyncOpenAI
from datasets import Dataset
from huggingface_hub import hf_hub_download

from dynaword.annotations.propella import (
    create_messages,
    AnnotationResponse,
    get_annotation_response_schema,
)
from src.config import MODEL, HF_TOKEN

client = AsyncOpenAI(base_url="http://sglang:8000/v1", api_key="EMPTY")

sem = asyncio.Semaphore(250)

async def async_annotate_document(document: str):
    """Asynchronously fetch a single document annotation."""
    async with sem:
        try:
            response = await client.chat.completions.create(
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
            response_content = response.choices[0].message.content

            result = AnnotationResponse.model_validate_json(response_content)
            return result.model_dump()
            
        except Exception as err:
            print(f"Error annotating document: {err}")
            raise err

def annotate_batch(batch):
    """Process a chunk of the dataset concurrently using the event loop."""
    async def process_all():
        tasks = [async_annotate_document(text) for text in batch["text"]]
        return await asyncio.gather(*tasks)

    results = asyncio.run(process_all())

    return {key: [res[key] for res in results] for key in results[0]}

def annotate_dataset(repo_id: str, remote_path: str, local_path: Path, dataset_name: str, revision: str | None = None, hf_token: str = HF_TOKEN) -> Path:
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
    
    metadata = ds.map(
        annotate_batch,
        batched=True,
        batch_size=1000, 
        remove_columns=[col for col in ds.column_names if col not in ["id", "dataset"]]
    )
    
    metadata.to_parquet(str(dest))
    return dest