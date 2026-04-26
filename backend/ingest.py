"""
Ingests YouTube transcripts from the Level Up Mortgages channel into ChromaDB.
Run this script once (or periodically) to populate/update the vector store.

Usage:
    python ingest.py
    python ingest.py --channel https://www.youtube.com/@LevelUpMortgages
    python ingest.py --video VIDEO_ID   # ingest a single video
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import chromadb
from chromadb.utils import embedding_functions

load_dotenv(Path(__file__).parent.parent / ".env")

# On Railway, set CHROMA_PATH to the mounted volume path, e.g. /data/chroma_db
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(Path(__file__).parent / "chroma_db")))
COLLECTION_NAME = "level_up_mortgages"
CHUNK_WORD_LIMIT = 250
EMBED_MODEL = "text-embedding-3-small"


def get_embedding_function():
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name=EMBED_MODEL,
    )


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    ef = get_embedding_function()
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


def get_channel_videos(channel_url: str) -> List[dict]:
    """Uses yt-dlp to fetch all video IDs and titles from a channel."""
    print(f"Fetching video list from: {channel_url}")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s",
        "--no-warnings",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"yt-dlp error: {result.stderr}", file=sys.stderr)
        return []

    videos = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            video_id, title = parts
            videos.append({"id": video_id.strip(), "title": title.strip()})
    print(f"Found {len(videos)} videos")
    return videos


_ytt = YouTubeTranscriptApi()


def get_transcript(video_id: str) -> Optional[List[dict]]:
    """Returns list of {text, start, duration} dicts, or None if unavailable."""
    try:
        fetched = _ytt.fetch(video_id, languages=["en", "en-US", "en-GB"])
        return [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]
    except (TranscriptsDisabled, NoTranscriptFound):
        try:
            transcript_list = _ytt.list(video_id)
            t = transcript_list.find_generated_transcript(["en", "en-US"])
            fetched = t.fetch()
            return [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]
        except Exception:
            pass
    except Exception as e:
        print(f"  Transcript error for {video_id}: {e}")
    return None


def chunk_transcript(transcript: List[dict], video_id: str, title: str) -> List[dict]:
    """
    Groups transcript segments into word-limited chunks, preserving the start
    timestamp of the first segment in each chunk so we can produce a deep link.
    """
    chunks = []
    current_words = []
    current_start = transcript[0]["start"] if transcript else 0.0

    for seg in transcript:
        words = seg["text"].split()
        if current_words and len(current_words) + len(words) > CHUNK_WORD_LIMIT:
            chunk_text = " ".join(current_words).strip()
            if chunk_text:
                t = int(current_start)
                url = f"https://www.youtube.com/watch?v={video_id}&t={t}s"
                chunks.append({
                    "text": chunk_text,
                    "video_id": video_id,
                    "title": title,
                    "start_time": current_start,
                    "url": url,
                })
            current_words = words
            current_start = seg["start"]
        else:
            current_words.extend(words)

    if current_words:
        chunk_text = " ".join(current_words).strip()
        if chunk_text:
            t = int(current_start)
            url = f"https://www.youtube.com/watch?v={video_id}&t={t}s"
            chunks.append({
                "text": chunk_text,
                "video_id": video_id,
                "title": title,
                "start_time": current_start,
                "url": url,
            })

    return chunks


def ingest_videos(videos: List[dict]):
    collection = get_collection()

    # Track already-ingested video IDs to avoid re-processing
    existing = set()
    try:
        results = collection.get(include=["metadatas"])
        for m in results["metadatas"]:
            existing.add(m["video_id"])
    except Exception:
        pass

    total_chunks = 0
    for i, video in enumerate(videos):
        vid_id = video["id"]
        title = video["title"]
        if vid_id in existing:
            print(f"[{i+1}/{len(videos)}] Skipping (already indexed): {title}")
            continue

        print(f"[{i+1}/{len(videos)}] Processing: {title}")
        transcript = get_transcript(vid_id)
        if transcript is None:
            print("  No transcript available, skipping.")
            continue

        chunks = chunk_transcript(transcript, vid_id, title)
        if not chunks:
            continue

        ids = [f"{vid_id}_chunk_{j}" for j in range(len(chunks))]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "video_id": c["video_id"],
                "title": c["title"],
                "start_time": c["start_time"],
                "url": c["url"],
            }
            for c in chunks
        ]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"  Added {len(chunks)} chunks")

    print(f"\nDone. Total new chunks added: {total_chunks}")
    print(f"Collection size: {collection.count()} chunks")


def main():
    parser = argparse.ArgumentParser(description="Ingest Level Up Mortgages YouTube transcripts")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--channel", default=os.getenv("YOUTUBE_CHANNEL_URL", "https://www.youtube.com/@LevelUpMortgages"))
    group.add_argument("--video", help="Ingest a single video by ID")
    args = parser.parse_args()

    if args.video:
        videos = [{"id": args.video, "title": f"Video {args.video}"}]
        # Try to get actual title
        try:
            cmd = ["yt-dlp", "--print", "%(title)s", "--no-warnings", f"https://www.youtube.com/watch?v={args.video}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                videos[0]["title"] = result.stdout.strip()
        except Exception:
            pass
    else:
        videos = get_channel_videos(args.channel)

    if not videos:
        print("No videos found.")
        return

    ingest_videos(videos)


if __name__ == "__main__":
    main()
