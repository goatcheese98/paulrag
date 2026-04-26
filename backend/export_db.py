"""
Export local ChromaDB to JSON, then upload to Railway via the import endpoint.

Usage:
    python export_db.py --url https://paulrag-api-production.up.railway.app --token TOKEN
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import chromadb
from chromadb.utils import embedding_functions


def export_and_upload(api_url: str, token: str):
    chroma_path = Path(os.getenv("CHROMA_PATH", str(Path(__file__).parent / "chroma_db")))
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small",
    )
    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        col = client.get_collection("level_up_mortgages", embedding_function=ef)
    except Exception as e:
        print(f"Could not open collection: {e}")
        sys.exit(1)

    count = col.count()
    print(f"Exporting {count} chunks...")

    results = col.get(include=["documents", "metadatas", "embeddings"])
    embeddings = results["embeddings"]
    if embeddings is not None:
        embeddings = [e.tolist() if hasattr(e, "tolist") else e for e in embeddings]
    ids = results["ids"]
    documents = results["documents"]
    metadatas = results["metadatas"]

    batch_size = int(os.getenv("EXPORT_BATCH_SIZE", "50"))
    print(f"Uploading to {api_url}/api/admin/import-db in batches of {batch_size} ...")

    import urllib.request

    total_uploaded = 0
    for start in range(0, len(ids), batch_size):
        end = min(start + batch_size, len(ids))
        payload = {
            "ids": ids[start:end],
            "documents": documents[start:end],
            "metadatas": metadatas[start:end],
            "embeddings": embeddings[start:end] if embeddings is not None else None,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{api_url}/api/admin/import-db",
            data=data,
            headers={"Content-Type": "application/json", "x-admin-token": token},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        total_uploaded += end - start
        print(f"  Uploaded {total_uploaded}/{len(ids)} chunks:", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    export_and_upload(args.url, args.token)
