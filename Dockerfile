FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY dynaword /app/dynaword
COPY annotator-bot/requirements.txt /app/annotator-bot/

WORKDIR /app/annotator-bot
RUN uv pip install --system --no-cache -r requirements.txt

COPY annotator-bot /app/annotator-bot
COPY config.yaml /app/config.yaml

EXPOSE 8080

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]