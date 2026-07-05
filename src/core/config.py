import os

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"[RepoMind] Required environment variable '{key}' is not set. "
            f"Please add it to your .env file."
        )
    return val


GROQ_API_KEY: str = _require("GROQ_API_KEY")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")  # optional — only needed for PR creation

# ─── Model selection ──────────────────────────────────────────────────────
# llama-3.1-8b-instant and llama-3.3-70b-versatile were deprecated by Groq
# (announced 2026-06-17). Groq's official migration guidance:
#   llama-3.1-8b-instant     -> openai/gpt-oss-20b
#   llama-3.3-70b-versatile  -> openai/gpt-oss-120b (or qwen/qwen3.6-27b)
# Kept configurable via env vars so future model swaps don't require code changes.
GROQ_MODEL_STRONG: str = os.getenv("GROQ_MODEL_STRONG", "openai/gpt-oss-120b")  # bug detection, fix generation, repo analysis
GROQ_MODEL_FAST: str = os.getenv("GROQ_MODEL_FAST", "openai/gpt-oss-20b")       # reflection, retry/stop planning

MCP_URL: str = os.getenv("MCP_URL", "http://localhost:9000/tool")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

MAX_ANALYSIS_FILES: int = int(os.getenv("MAX_ANALYSIS_FILES", "30"))
MAX_FIX_LINES: int = int(os.getenv("MAX_FIX_LINES", "150"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
MCP_TIMEOUT: int = int(os.getenv("MCP_TIMEOUT", "30"))   # seconds
TEST_TIMEOUT: int = int(os.getenv("TEST_TIMEOUT", "300")) # seconds
