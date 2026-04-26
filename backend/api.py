"""
FastAPI server exposing the RAG chatbot.

Run with:
    uvicorn api:app --reload --port 8000
"""

import io
import json
import os
import shutil
import tarfile
from typing import List
from fastapi import FastAPI, Header, HTTPException, UploadFile, File
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


@app.post("/api/admin/seed-db")
async def seed_db(file: UploadFile = File(...), x_admin_token: str = Header(...)):
    """Upload a .tar.gz of the chroma_db directory to populate the Railway volume."""
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    chroma_path = Path(os.getenv("CHROMA_PATH", "/data/chroma_db"))

    # Wipe existing data and replace with uploaded archive
    if chroma_path.exists():
        shutil.rmtree(chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)

    contents = await file.read()
    with tarfile.open(fileobj=io.BytesIO(contents), mode="r:gz") as tar:
        tar.extractall(path=chroma_path)

    return get_status()
