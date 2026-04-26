#!/usr/bin/env bash
# Check actual ChromaDB chunk count — if zero, run ingestion in background.
set -e

CHROMA="${CHROMA_PATH:-/data/chroma_db}"

CHUNK_COUNT=$(python3 - <<'PYEOF'
import os, sys
from pathlib import Path
try:
    import chromadb
    client = chromadb.PersistentClient(path=os.environ.get("CHROMA_PATH", "/data/chroma_db"))
    col = client.get_collection("level_up_mortgages")
    print(col.count())
except Exception:
    print(0)
PYEOF
)

echo "Current ChromaDB chunk count: $CHUNK_COUNT"

if [ "$CHUNK_COUNT" -eq 0 ]; then
  echo "No data found — starting background ingestion..."
  python ingest.py &
  echo "Ingestion running (PID $!). API starting now."
else
  echo "ChromaDB already populated ($CHUNK_COUNT chunks). Skipping ingestion."
fi

exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-8000}"
