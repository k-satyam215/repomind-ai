"""
RepoMind Simple Memory

Stores bug+fix history for the pipeline's reflection loop.

Storage strategy:
- Redis available  → store in Redis list (persistent, fast, shared across workers)
- Redis unavailable → fallback to local JSON file (single-process safe)

This is separate from vector_memory (ChromaDB semantic search).
simple_memory stores the raw history; vector_memory stores embeddings.
"""

import json
import os
import threading
from typing import List

from src.core.config import REDIS_ENABLED
from src.core.logger import get_logger

logger = get_logger("RepoMind.SimpleMemory")

MEMORY_FILE = "memory_store.json"
REDIS_KEY = "repomind:memory"
_lock = threading.Lock()


def _get_redis():
    if not REDIS_ENABLED:
        return None
    try:
        from src.core.cache import _get_client
        return _get_client()
    except Exception:
        return None


# ── Save ──────────────────────────────────────────────────────────────────────

def save_memory(entry: dict) -> None:
    """
    Persist a bug+fix entry.
    Uses Redis RPUSH if available, else appends to local JSON file.
    """
    client = _get_redis()

    if client:
        try:
            client.rpush(REDIS_KEY, json.dumps(entry, default=str))
            # Keep last 500 entries
            client.ltrim(REDIS_KEY, -500, -1)
            logger.debug("Memory saved to Redis")
            return
        except Exception as e:
            logger.warning(f"Redis memory save failed, falling back to file: {e}")

    # Fallback: local JSON
    with _lock:
        try:
            data: List[dict] = []
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

            data.append(entry)
            # Keep last 500 entries
            data = data[-500:]

            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Memory saved to file. Total entries: {len(data)}")

        except Exception as e:
            logger.error(f"Failed to save memory: {e}")


# ── Load ──────────────────────────────────────────────────────────────────────

def load_memory() -> List[dict]:
    """
    Load all stored entries.
    Reads from Redis if available, else local JSON file.
    """
    client = _get_redis()

    if client:
        try:
            raw_list = client.lrange(REDIS_KEY, 0, -1)
            entries = []
            for raw in raw_list:
                try:
                    entries.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            logger.debug(f"Loaded {len(entries)} entries from Redis memory")
            return entries
        except Exception as e:
            logger.warning(f"Redis memory load failed, falling back to file: {e}")

    # Fallback: local JSON
    with _lock:
        try:
            if not os.path.exists(MEMORY_FILE):
                return []
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Loaded {len(data)} entries from file memory")
            return data
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return []
