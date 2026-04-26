"""
FastAPI server exposing the Level Up Mortgages RAG chatbot.

Run locally:
    uvicorn api:app --reload --port 8000
"""

import json
import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

from rag import stream_answer, get_status

app = FastAPI(title="Level Up Mortgages RAG API")

_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:3000",
)
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
origin_regex = os.getenv(
    "ALLOWED_ORIGIN_REGEX",
    r"https://([a-z0-9-]+\.)?paulrag\.pages\.dev$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
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
