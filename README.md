# Dynaword Annotation Server

An automated annotation bot and server for [Dynaword](https://huggingface.co/danish-foundation-models) Hugging Face dataset repositories.

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

2. **`annotator-bot/` (FastAPI)**
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

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (required for the GPU reservation in [`docker-compose.yml`](./docker-compose.yml); remove the `deploy` block if running on CPU only)

### 1. Prepare Required Directories
The [`Dockerfile`](./Dockerfile) expects `dynaword/` and `repos/` in the project root:
- Place the `dynaword` repository/package at `./dynaword` (installed into the image via `annotator-bot/requirements.txt`).
- Create the `./repos` directory if it does not exist yet:
  ```bash
  mkdir -p repos
  ```
  It is mounted into the container at `/app/repos`, where the bot clones the Hugging Face repositories listed in [`config.yaml`](./config.yaml) on startup.

### 2. Configure Environment and Settings
Create a `.env` file in the project root:
```env
HF_TOKEN=hf_...
WEBHOOK_SECRET=your_webhook_shared_secret
```

Edit [`config.yaml`](./config.yaml) to configure the bot `name`, `hf_repo_ids`, `model`, `webhook_url`, and polling `interval_minutes`.

### 3. Build and Run
Build and start the bot with Docker Compose:
```bash
docker compose up --build -d
```

The FastAPI server is exposed on port `8080` (`http://localhost:8080`).

Useful commands:
```bash
# Follow container logs
docker compose logs -f

# Stop the container
docker compose down
```

