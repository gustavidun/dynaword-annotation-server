# Dynaword Annotation Server

A FastAPI server that periodically checks a Dynaword Hugging Face repository for unannotated datasets and automatically annotates them using a local LLM inference server.

## How it works

On every scheduler tick (configurable interval), the server:

1. Lists all `data/*/` folders in the HF dataset repo
2. Identifies any folder **missing** a `metadata.parquet` file
3. For each unannotated dataset, runs the annotation pipeline using a local OpenAI-compatible inference endpoint (e.g. llama.cpp or vLLM)
4. Saves the result to `out/<dataset>/metadata.parquet` locally
5. Opens a PR on the HF repo uploading the `metadata.parquet`

## 📁 Repository Structure

```
dynaword-annotation-server/
├── src/
│   ├── __init__.py
│   ├── annotate.py      # annotation pipeline
│   ├── config.py        # reads config.yaml
│   ├── db.py
│   ├── hf.py            # HF API helpers
│   └── main.py          # FastAPI app + scheduler
├── out/                 # generated annotation output (gitignored)
├── config.yaml          # runtime configuration
├── .gitignore
├── README.md
└── requirements.txt
```

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure** [`config.yaml`](./config.yaml):
   ```yaml
   hf_repo_id: "username/dataset_name"
   interval_minutes: 5
   model: "mradermacher/propella-1-4b-GGUF"
   ```

3. **Start a local inference server** (e.g. llama.cpp) on `http://localhost:8000/v1`

4. **Run the server** (using a different port than the inference server):
   ```bash
   uvicorn src.main:app --reload --port 8080
   ```

## ⚙️ Configuration

All settings live in [`config.yaml`](./config.yaml):

| Key | Default | Description |
|---|---|---|
| `hf_repo_id` | `gustavidunsloth/multilingual-dynaword-3` | HF dataset repo to watch |
| `interval_minutes` | `5` | How often to check for unannotated datasets |
| `model` | `mradermacher/propella-1-4b-GGUF` | Model name passed to the inference server |

## 📤 Output

Annotated parquet files are written to `out/<dataset_name>/metadata.parquet` and uploaded to the HF repo as a pull request.
