FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m playwright install chromium --with-deps

COPY . .

RUN mkdir -p logs exports reports/charts /app/ms-playwright

CMD python -m playwright install chromium --with-deps 2>&1 && \
    streamlit run streamlit_app.py --server.port=10000 --server.address=0.0.0.0
