"""
HuggingFace Spaces entry point for RepoMind AI.

This file wraps the Streamlit frontend for deployment on HuggingFace Spaces.
The backend runs in the same process for Spaces compatibility (no separate services).

Environment variables required in HF Spaces secrets:
  GROQ_API_KEY   — Groq API key (required)
  GITHUB_TOKEN   — GitHub PAT for PR creation (optional)

Deploy:
  - Create a new HuggingFace Space (Docker SDK)
  - Set secrets: GROQ_API_KEY, GITHUB_TOKEN
  - Push this repo — GitHub Actions handles the rest via .github/workflows/hf-deploy.yml
"""

import os
import subprocess
import sys
import threading
import time

# ── Start MCP server in background ───────────────────────────────────────────
def _start_mcp():
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.mcp.server:app",
         "--host", "127.0.0.1", "--port", "9000"],
        env={**os.environ, "PYTHONPATH": "."},
    )

# ── Start FastAPI backend in background ──────────────────────────────────────
def _start_backend():
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "0.0.0.0", "--port", "8000"],
        env={**os.environ, "PYTHONPATH": ".", "MCP_URL": "http://localhost:9000/tool"},
    )

def _wait_for_port(port: int, timeout: int = 30):
    """Block until a local port is accepting connections."""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False

if __name__ == "__main__":
    print("🚀 Starting RepoMind AI on HuggingFace Spaces...")

    mcp_thread = threading.Thread(target=_start_mcp, daemon=True)
    mcp_thread.start()
    _wait_for_port(9000)
    print("✅ MCP server ready on :9000")

    backend_thread = threading.Thread(target=_start_backend, daemon=True)
    backend_thread.start()
    _wait_for_port(8000)
    print("✅ Backend ready on :8000")

    # Launch Streamlit frontend (blocking)
    os.execvp(sys.executable, [
        sys.executable, "-m", "streamlit", "run", "frontend/app.py",
        "--server.port", "7860",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])
