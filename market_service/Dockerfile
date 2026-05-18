FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN sed '/^[[:space:]]*$/q' requirements.txt | sed '/^[[:space:]]*$/d' > requirements.runtime.txt \
    && pip install --no-cache-dir --default-timeout=120 -r requirements.runtime.txt

COPY src/ ./src/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY seed_data.py ./
COPY entrypoint.sh ./

RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://localhost:{os.getenv('PORT', '8001')}/health\")" || exit 1

CMD ["sh", "./entrypoint.sh"]
