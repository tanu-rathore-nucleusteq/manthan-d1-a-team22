#!/bin/sh
# Container entrypoint: apply migrations, seed demo data if the database is empty, start the API.
set -e
alembic upgrade head
python -m scripts.seed --if-empty
exec uvicorn returnright.main:app --host 0.0.0.0 --port 8000 --proxy-headers
