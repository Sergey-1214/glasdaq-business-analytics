FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN sed '/^[[:space:]]*$/q' requirements.txt | sed '/^[[:space:]]*$/d' > requirements.runtime.txt \
    && pip install --no-cache-dir --default-timeout=120 -r requirements.runtime.txt

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY app ./app
COPY entrypoint.sh ./entrypoint.sh

RUN sed -i 's/\r$//' ./entrypoint.sh && chmod +x ./entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8007/health')" || exit 1

CMD ["./entrypoint.sh"]
