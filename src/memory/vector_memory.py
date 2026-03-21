import chromadb
from chromadb.config import Settings
import hashlib
import os

PERSIST_DIR = "./repomind_memory"

os.makedirs(PERSIST_DIR, exist_ok=True)

client = chromadb.Client(
    Settings(
        persist_directory=PERSIST_DIR
    )
)

collection = client.get_or_create_collection(
    name="repomind_memory"
)


def _generate_id(text: str):
    return hashlib.sha256(text.encode()).hexdigest()


def save_vector_memory(bug, fix):

    doc = str(bug) + "\nFIX:\n" + fix
    doc_id = _generate_id(doc)

    try:
        collection.add(
            documents=[doc],
            ids=[doc_id]
        )
        client.persist()

    except Exception:
        pass


def search_similar_bug(bug, top_k=1):

    try:
        res = collection.query(
            query_texts=[str(bug)],
            n_results=top_k
        )

        if not res["documents"]:
            return None

        return res["documents"][0][0]

    except Exception:
        return None