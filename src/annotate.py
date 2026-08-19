
from typing import cast
from dynaword.annotations.propella import (
    create_messages,
    AnnotationResponse,
    get_annotation_response_schema,
)
from pathlib import Path

from openai import OpenAI
from datasets import load_dataset, Dataset
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

def annotate_dataset(remote_path: str, out_name: str) -> Path:
    dest = ROOT / "out" / out_name / "metadata.parquet"
    ds = load_dataset(HF_REPO_ID, data_files=f"{remote_path}/data.parquet", split="train")
    metadata = ds.map(annotate_sample, batched=False, num_proc=8, remove_columns=ds.column_names)
    metadata.to_parquet(str(dest))
    return dest