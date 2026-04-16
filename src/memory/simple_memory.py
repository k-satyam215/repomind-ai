import json
import os
import threading
from typing import List

from src.core.logger import get_logger

logger = get_logger("RepoMind.SimpleMemory")

MEMORY_FILE = "memory_store.json"
_lock = threading.Lock()


def save_memory(entry: dict) -> None:
    """Thread-safe append to JSON memory store."""
    with _lock:
        try:
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data: List[dict] = json.load(f)
            else:
                data = []

            data.append(entry)

            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Memory saved. Total entries: {len(data)}")

        except Exception as e:
            logger.error(f"Failed to save memory: {e}")


def load_memory() -> List[dict]:
    """Thread-safe read from JSON memory store."""
    with _lock:
        try:
            if not os.path.exists(MEMORY_FILE):
                return []
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return []
