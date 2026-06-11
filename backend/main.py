import os
import shutil

from fastapi import FastAPI, Request
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
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
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
    try:
        total, used, free = shutil.disk_usage("/tmp")
        free_mb = free // (1024 * 1024)
        checks["tmp_space_mb"] = free_mb
        checks["tmp_space"] = "ok" if free_mb > 500 else "low"
    except Exception:
        checks["tmp_space"] = "unknown"

    overall = "ok" if all(
        v in ("ok", checks.get("tmp_space_mb", "ok"))
        for k, v in checks.items()
        if k != "tmp_space_mb"
    ) else "degraded"

    # Groq key missing = not degraded, just warn (can still run with env-injected key)
    if checks["groq_api_key"] == "missing":
        overall = "degraded"

    status_code = 200 if overall == "ok" else 207
    return JSONResponse(
        content={"status": overall, "version": "1.2.0", "checks": checks},
        status_code=status_code,
    )
