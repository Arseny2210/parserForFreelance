FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Node.js for building the React frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi && \
    python -m playwright install chromium --with-deps

COPY . .

RUN cd frontend && npm install && npm run build

RUN mkdir -p logs exports reports/charts /app/ms-playwright

EXPOSE 8000

CMD uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
