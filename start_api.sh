#!/usr/bin/env bash
# Starts the FastAPI backend. Run from the repository root directory.
set -e

cd "$(dirname "$0")"
source .venv/bin/activate
set -a; source .env; set +a
cd backend
exec uvicorn api:app --reload --host 0.0.0.0 --port 8000
