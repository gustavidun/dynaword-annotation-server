# Dynaword Annotation Server

An automated annotation bot and server for [Dynaword](https://huggingface.co/danish-foundation-models) Hugging Face dataset repositories. It processes dataset annotations using a local LLM inference server (`llama-server`), runs validation tests, updates descriptive statistics and charts, and commits results directly to pull requests.

---

### Commands

When a contributor opens a PR with a new dataset, you can trigger the bot by commenting on the PR discussion:

```
@<bot-name> annotate <dataset_name>
```
*(where `<bot-name>` matches `name` in `config.yaml`, e.g., `@dynaword-bot annotate my_dataset`)*

The bot will:
1. Generate synthetic metadata (`metadata.parquet`).
2. Run tests and capture output to `test_results.log`.
3. Run `update_descriptive_statistics.py`.
4. Commit and push all generated files to the PR.

---

## Architecture

The system consists of two primary components:

1. **`webhooks/` (Cloudflare Worker + D1 Database)**
   - Receives incoming webhooks from Hugging Face (e.g., new comments in PR discussions) and stores them in database.
   - Provides authenticated endpoints for the local bot to poll and mark webhooks as completed.
   - Runs a daily cron cleanup for events older than 7 days.

2. **`annotator-bot/` (FastAPI Service)**
   - Periodically polls the Cloudflare Worker for pending webhook events.
   - Listens for bot commands in PR comments (e.g. `@<name> annotate <dataset>`).
   - Runs annotation, executes tests, updates descriptive statistics, and pushes commits to PR.

```
┌─────────────────┐       Webhook       ┌────────────────────────┐
│  Hugging Face   │ ──────────────────> │   Cloudflare Worker    │
│   (dynaword)    │                     │     (D1 Database)      │
└─────────────────┘                     └────────────────────────┘
        ▲                                   │   ▲
        │ Push to PR           Poll pending │   │ Mark completed
        │                                   ▼   │
┌────────────────────────────────────────────────────────────────┐
│                         Annotator Bot                          │
│                (running locally on DGX Spark)                  │
└────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Environment
Create a `.env` file in the project root:
```env
HF_TOKEN=hf_...
WEBHOOK_SECRET=your_webhook_shared_secret
```

Edit [`config.yaml`](./config.yaml).

### 2. Deploy Webhooks Worker (Cloudflare)
If not already deployed:
```bash
cd webhooks
npm install
npx wrangler d1 execute dynaword-webhooks --remote --file=schema.sql
npx wrangler secret put WEBHOOK_SECRET
npx wrangler deploy
cd ..
```
Set up a Hugging Face Webhook pointing to the worker URL with `WEBHOOK_SECRET`.

### 3. Start Local LLM Server
Run an LLM inference server locally with Propella on port 8000, i.e.:
```bash
llama-server --hf-repo mradermacher/propella-1-4b-GGUF:Q8_0 --port 8000
```

### 4. Run the Annotator Bot
Launch the FastAPI server locally on port 8080
```bash
uvicorn src.app:app --reload --port 8080
```

