import os
import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router
from src.core.logger import get_logger

logger = get_logger("RepoMind.API")

app = FastAPI(
    title="RepoMind AI",
    description="Autonomous Software Engineering Agent API",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:7860,http://localhost:8501"
    ).split(",") if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "RepoMind AI is running", "version": "1.2.0"}


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.2.0"}


@app.get("/health/detailed")
def health_detailed():
    """
    Deep health check — verifies critical dependencies are reachable.
    Used by Docker healthcheck and external monitors.
    """
    checks = {}

    # Check: Groq API key configured
    checks["groq_api_key"] = "ok" if os.getenv("GROQ_API_KEY") else "missing"

    # Check: MCP server reachable
    mcp_url = os.getenv("MCP_URL", "http://localhost:9000/tool")
    try:
        import urllib.request
        mcp_base = mcp_url.replace("/tool", "/docs")
        with urllib.request.urlopen(mcp_base, timeout=2):
            checks["mcp_server"] = "ok"
    except Exception:
        checks["mcp_server"] = "unreachable"

    # Check: memory directory writable
    try:
        mem_dir = "./repomind_memory"
        os.makedirs(mem_dir, exist_ok=True)
        test_file = os.path.join(mem_dir, ".healthcheck")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        checks["memory_dir"] = "ok"
    except Exception as e:
        checks["memory_dir"] = f"error: {e}"

    # Check: tmp space available (need at least 500MB for cloning repos)
    # tempfile.gettempdir() resolves to the correct OS temp dir on both
    # Windows (e.g. C:\Users\...\AppData\Local\Temp) and Linux/Docker (/tmp) --
    # a hardcoded "/tmp" silently misreports on Windows.
    try:
        import tempfile as _tempfile
        total, used, free = shutil.disk_usage(_tempfile.gettempdir())
        free_mb = free // (1024 * 1024)
        checks["tmp_space_mb"] = free_mb
        checks["tmp_space"] = "ok" if free_mb > 500 else "low"
    except Exception:
        checks["tmp_space"] = "unknown"

    # Overall status is "ok" only if every status-bearing check reports "ok".
    # tmp_space_mb is a raw number (not a status string) so it's excluded here.
    status_checks = {k: v for k, v in checks.items() if k != "tmp_space_mb"}
    overall = "ok" if all(v == "ok" for v in status_checks.values()) else "degraded"

    status_code = 200 if overall == "ok" else 207
    return JSONResponse(
        content={"status": overall, "version": "1.2.0", "checks": checks},
        status_code=status_code,
    )
