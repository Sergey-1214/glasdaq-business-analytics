#!/bin/sh
set -e
alembic upgrade head
python seed_data.py
exec python -m uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8001}"
