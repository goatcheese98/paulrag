"""
FastAPI server exposing the RAG chatbot.

Run with:
    uvicorn api:app --reload --port 8000
"""

import json
import os
from typing import Any, Dict, List
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

from rag import stream_answer, get_status

app = FastAPI(title="Level Up Mortgages RAG API")

# ALLOWED_ORIGINS: comma-separated list of allowed frontend origins.
# Set ALLOWED_ORIGINS in your Railway env vars to your Cloudflare Pages URL.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:3000",
)
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: List[Message] = []


def event_stream(question: str, history: List[dict]):
    for chunk in stream_answer(question, history):
        if isinstance(chunk, str):
            data = json.dumps({"type": "text", "content": chunk})
        else:
            data = json.dumps({"type": "sources", "sources": chunk["sources"]})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in req.history]
    return StreamingResponse(
        event_stream(req.question, history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/status")
async def status():
    return get_status()


class ImportPayload(BaseModel):
    ids: List[str]
    documents: List[str]
    metadatas: List[Dict[str, Any]]
    embeddings: List[List[float]]


@app.post("/api/admin/import-db")
async def import_db(payload: ImportPayload, x_admin_token: str = Header(...)):
    """Import pre-computed documents + embeddings into ChromaDB on Railway."""
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    import chromadb
    from chromadb.utils import embedding_functions

    chroma_path = Path(os.getenv("CHROMA_PATH", "/data/chroma_db"))
    chroma_path.mkdir(parents=True, exist_ok=True)

    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small",
    )
    client = chromadb.PersistentClient(path=str(chroma_path))

    # Drop and recreate the collection so this is idempotent
    try:
        client.delete_collection("level_up_mortgages")
    except Exception:
        pass
    col = client.create_collection("level_up_mortgages", embedding_function=ef)

    # Insert in batches of 100 to avoid memory issues
    batch = 100
    ids, docs, metas, embs = payload.ids, payload.documents, payload.metadatas, payload.embeddings
    for i in range(0, len(ids), batch):
        col.add(
            ids=ids[i:i+batch],
            documents=docs[i:i+batch],
            metadatas=metas[i:i+batch],
            embeddings=embs[i:i+batch],
        )

    return get_status()
