FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# install git, git-lfs and chromium
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    chromium \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/chromium /usr/bin/google-chrome \
    && git config --global --add safe.directory '*' \
    && git lfs install

WORKDIR /app

COPY dynaword /app/dynaword
COPY annotator-bot/requirements.txt /app/annotator-bot/

WORKDIR /app/annotator-bot
RUN uv pip install --system --no-cache -r requirements.txt

COPY repos /app/repos
COPY annotator-bot /app/annotator-bot
COPY config.yaml /app/config.yaml

EXPOSE 8080

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]