# Anonimization pipeline — application image.
# Runs the CLI. The local LLM (Ollama) runs as a separate service; this image
# never needs network access beyond talking to that local Ollama.
FROM python:3.12-slim

# Keep Python lean and predictable in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY pipeline/ ./pipeline/
COPY cli.py config.yaml ./

# Non-root user; mounted data dirs are created/owned at runtime via compose.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/vaults /app/out /data \
    && chown -R appuser:appuser /app /data
USER appuser

# Default: stay alive so you can `docker compose exec pipeline python cli.py ...`.
CMD ["sleep", "infinity"]
