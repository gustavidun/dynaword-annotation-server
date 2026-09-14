FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY annotator-bot/requirements.txt .
COPY dynaword /dynaword

RUN uv pip install --system --no-cache -r requirements.txt

COPY dynaword /app/dynaword
COPY annotator-bot /app/annotator-bot
COPY config.yaml /app/config.yaml

WORKDIR /app/annotator-bot

EXPOSE 8080

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]