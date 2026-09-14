FROM python:3.11-slim

WORKDIR /app

# Copy the dependencies
COPY dynaword /app/dynaword
COPY annotator-bot /app/annotator-bot
COPY config.yaml /app/config.yaml

WORKDIR /app/annotator-bot

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]
