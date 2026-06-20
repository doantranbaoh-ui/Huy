# --- Dockerfile (Poetry) ---
FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (no Rust)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application
COPY . .

CMD ["poetry", "run", "uvicorn", "proxy_manager.app:app", "--host", "0.0.0.0", "--port", "8000"]
