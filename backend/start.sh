#!/usr/bin/env bash
# On first boot (empty volume), start ingestion in background then launch API.
# On subsequent boots the data is already there — just start the API.
set -e

CHROMA="${CHROMA_PATH:-/data/chroma_db}"

if [ ! -d "$CHROMA" ] || [ -z "$(ls -A "$CHROMA" 2>/dev/null)" ]; then
  echo "ChromaDB is empty — starting background ingestion..."
  python ingest.py &
  echo "Ingestion running in background (PID $!). API starting now."
fi

exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-8000}"
