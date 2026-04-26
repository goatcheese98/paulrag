"""
RAG pipeline: query ChromaDB and generate answers with OpenAI gpt-4.1-mini,
including YouTube timestamp links in the response.
"""

import os
from pathlib import Path
from typing import Optional, List

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# On Railway, set CHROMA_PATH to the mounted volume path, e.g. /data/chroma_db
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(Path(__file__).parent / "chroma_db")))
COLLECTION_NAME = "level_up_mortgages"
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4.1-mini"
N_RESULTS = 6

SYSTEM_PROMPT = """You are Level Up Channel Bot, an expert mortgage advisor AI assistant for the "Level Up Mortgages" YouTube channel hosted by Paul Davidescu.

You answer questions about mortgages, home buying, refinancing, real estate financing, and related financial topics using Paul's video content as your knowledge base.

When answering:
- Be clear, friendly, and approachable — match Paul's educational style
- Structure your answers with clear headings or bullet points when helpful
- Always cite your sources using the exact YouTube links provided in the context
- Format video citations as: [📹 Video Title](YouTube URL with timestamp) — so users can watch the relevant section
- If the context doesn't contain enough information, say so and suggest the user search Paul's channel directly
- Never make up mortgage advice not supported by the provided context
- Include timestamps in links whenever they are available (e.g. ?t=123s)

The context below contains transcript excerpts from Paul's videos. Each excerpt includes its source URL with timestamp."""


def _openai_ef():
    api_key = os.getenv("OPENAI_API_KEY")
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBED_MODEL,
    )


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    ef = _openai_ef()
    try:
        return client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    except Exception:
        return None


def query_context(question: str, n_results: int = N_RESULTS) -> List[dict]:
    collection = get_collection()
    if collection is None or collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[question],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "title": meta.get("title", "Unknown Video"),
            "video_id": meta.get("video_id", ""),
            "start_time": meta.get("start_time", 0),
            "url": meta.get("url", ""),
            "relevance_score": 1 - dist,
        })

    return chunks


def build_context_block(chunks: List[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        minutes = int(chunk["start_time"] // 60)
        seconds = int(chunk["start_time"] % 60)
        timestamp_label = f"{minutes}:{seconds:02d}"
        parts.append(
            f"[Source {i}] \"{chunk['title']}\" at {timestamp_label}\n"
            f"URL: {chunk['url']}\n"
            f"Excerpt: {chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def stream_answer(question: str, history: Optional[List[dict]] = None):
    """
    Generator that yields text chunks (str) while streaming,
    then yields {"sources": [...]} as the final item.
    """
    chunks = query_context(question)

    if not chunks:
        yield "I don't have any video content indexed yet. Please run the ingestion script first to load Paul's videos into the knowledge base."
        yield {"sources": []}
        return

    context = build_context_block(chunks)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"CONTEXT FROM PAUL'S VIDEOS:\n\n{context}\n\n---\n\nQUESTION: {question}",
    })

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with client.chat.completions.create(
        model=CHAT_MODEL,
        max_tokens=1500,
        messages=messages,
        stream=True,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta is not None:
                yield delta

    # Deduplicate sources by video_id, keep highest relevance per video
    seen: dict[str, dict] = {}
    for chunk in chunks:
        vid = chunk["video_id"]
        if vid not in seen or chunk["relevance_score"] > seen[vid]["relevance_score"]:
            seen[vid] = chunk

    sources = [
        {
            "title": c["title"],
            "url": c["url"],
            "video_id": c["video_id"],
            "start_time": c["start_time"],
            "relevance_score": round(c["relevance_score"], 3),
        }
        for c in sorted(seen.values(), key=lambda x: x["relevance_score"], reverse=True)
    ]

    yield {"sources": sources}


def get_status() -> dict:
    collection = get_collection()
    if collection is None:
        return {"indexed": False, "chunk_count": 0, "video_count": 0}

    count = collection.count()
    if count == 0:
        return {"indexed": False, "chunk_count": 0, "video_count": 0}

    results = collection.get(include=["metadatas"])
    video_ids = {m.get("video_id") for m in results["metadatas"] if m.get("video_id")}

    return {
        "indexed": True,
        "chunk_count": count,
        "video_count": len(video_ids),
    }
