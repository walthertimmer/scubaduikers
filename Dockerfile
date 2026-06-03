FROM python:3.13-slim

WORKDIR /app

# Install dependencies before copying app code so this layer is cached
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY . .

# Create a non-root user and a directory for the SQLite database
RUN mkdir -p /data \
    && useradd --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app /data

USER appuser

ENV DATABASE_PATH=/data/scubaduikers.db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
