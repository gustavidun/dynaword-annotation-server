# Dynaword Annotation Server

A FastAPI server that periodically checks a Dynaword Hugging Face repository for unannotated datasets and automatically annotates them using a local LLM inference server.

## How it works

On every tick, the server:

1. Lists all `data/*/` folders in the HF dataset repo
2. Identifies any folder **missing** a `metadata.parquet` file
3. Creates annotations
4. Saves the result to `out/<dataset>/metadata.parquet` locally
5. Opens a PR on the HF repo uploading the `metadata.parquet`

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure** [`config.yaml`](./config.yaml):

3. **Start a local inference server** on `http://localhost:8000/v1`

4. **Run the server** (using a different port than the inference server):
   ```bash
   uvicorn src.main:app --reload --port 8080
   ```

## Output

Annotated parquet files are written to `out/<dataset_name>/metadata.parquet` and uploaded to the HF repo as a pull request.
