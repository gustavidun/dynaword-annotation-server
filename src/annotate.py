
from typing import cast
from dynaword.annotations.propella import (
    create_messages,
    AnnotationResponse,
    get_annotation_response_schema,
)
from pathlib import Path

from openai import OpenAI
from datasets import Dataset
from huggingface_hub import hf_hub_download
from src.config import MODEL, HF_REPO_ID, ROOT

def annotate_document(document: str):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

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
    response_content = response.choices[0].message.content
    result = AnnotationResponse.model_validate_json(response_content)
    return result


def annotate_sample(example):
    result = annotate_document(example["text"])
    return result.model_dump()

def annotate_dataset(remote_path: str, out_name: str, revision: str | None = None) -> Path:
    dest = ROOT / "out" / out_name / "metadata.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    local_parquet = hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=remote_path,
        repo_type="dataset",
        revision=revision,
        force_download=True
    )
    
    ds = Dataset.from_parquet(local_parquet)
    metadata = ds.map(annotate_sample, batched=False, num_proc=8, remove_columns=ds.column_names)
    metadata.to_parquet(str(dest))
    return dest