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
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")  # optional

# ─── Model selection ──────────────────────────────────────────────────────────
GROQ_MODEL_STRONG: str = os.getenv("GROQ_MODEL_STRONG", "openai/gpt-oss-120b")
GROQ_MODEL_FAST: str = os.getenv("GROQ_MODEL_FAST", "openai/gpt-oss-20b")

# ─── LangSmith tracing ────────────────────────────────────────────────────────
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "repomind-ai")
LANGSMITH_TRACING_ENABLED: bool = bool(
    LANGSMITH_API_KEY
    and os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
)

# Auto-configure LangSmith env vars so all LangChain/LangGraph calls are traced
if LANGSMITH_TRACING_ENABLED:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

# ─── Redis ────────────────────────────────────────────────────────────────────
# Used for:
#   1. Caching repo analysis results (avoid re-cloning same repo)
#   2. Rate-limit tracking per repo URL
#   3. Persistent job queue for async analysis (future)
REDIS_URL: str = os.getenv("REDIS_URL", "")
REDIS_ENABLED: bool = bool(REDIS_URL)
REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # seconds

# ─── URLs ─────────────────────────────────────────────────────────────────────
MCP_URL: str = os.getenv("MCP_URL", "http://localhost:9000/tool")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

# ─── Tuning ───────────────────────────────────────────────────────────────────
MAX_ANALYSIS_FILES: int = int(os.getenv("MAX_ANALYSIS_FILES", "30"))
MAX_FIX_LINES: int = int(os.getenv("MAX_FIX_LINES", "150"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
MCP_TIMEOUT: int = int(os.getenv("MCP_TIMEOUT", "30"))
TEST_TIMEOUT: int = int(os.getenv("TEST_TIMEOUT", "300"))
