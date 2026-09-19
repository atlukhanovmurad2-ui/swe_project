FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai/ ./ai/
COPY foodanalyzer/ ./foodanalyzer/
COPY data/ ./data/
COPY config.py demo_ai.py pyproject.toml ./

EXPOSE 8000
ENV HTTP_PORT=8000 LOG_LEVEL=INFO

# Default: run the HTTP API. Override the command to use the CLI, e.g.
#   docker run --rm foodanalyzer python -m foodanalyzer analyze data/rice_chicken.png --offline
CMD ["python", "-m", "foodanalyzer.api"]
