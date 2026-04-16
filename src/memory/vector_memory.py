import hashlib
import os
from typing import Optional
from src.core.logger import get_logger

logger = get_logger("RepoMind.VectorMemory")

PERSIST_DIR = "./repomind_memory"
os.makedirs(PERSIST_DIR, exist_ok=True)

# Lazy init — avoids import-time crash if chromadb not installed
_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb

        # PersistentClient replaces deprecated Client(Settings(persist_directory=...))
        # persist() call is also removed — persistence is automatic in chromadb >= 0.4
        client = chromadb.PersistentClient(path=PERSIST_DIR)
        _collection = client.get_or_create_collection(name="repomind_memory")
        logger.info("ChromaDB vector memory initialized")
        return _collection

    except Exception as e:
        logger.error(f"ChromaDB init failed: {e}")
        return None


def _generate_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def save_vector_memory(bug: dict, fix: str) -> None:
    """
    Store a bug+fix pair as a vector document.
    Duplicate IDs are handled gracefully — upsert instead of add.
    """
    collection = _get_collection()
    if collection is None:
        return

    doc = str(bug) + "\nFIX:\n" + fix
    doc_id = _generate_id(doc)

    try:
        # upsert avoids duplicate ID errors (add raises on duplicate)
        collection.upsert(documents=[doc], ids=[doc_id])
        logger.debug("Vector memory saved")
    except Exception as e:
        logger.error(f"Failed to save vector memory: {e}")


def search_similar_bug(bug: dict, top_k: int = 1) -> Optional[str]:
    """
    Search for a previously seen similar bug and return its fix context.
    Returns None if nothing relevant found.
    """
    collection = _get_collection()
    if collection is None:
        return None

    try:
        res = collection.query(
            query_texts=[str(bug)],
            n_results=top_k
        )

        docs = res.get("documents", [[]])
        if docs and docs[0]:
            logger.debug("Similar bug found in vector memory")
            return docs[0][0]

        return None

    except Exception as e:
        logger.error(f"Vector memory search failed: {e}")
        return None
