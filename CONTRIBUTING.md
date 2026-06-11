# Contributing to RepoMind AI

Thank you for your interest in contributing. This document covers how to set up the project locally, run tests, and submit a pull request.

---

## Prerequisites

- Python 3.11+
- Docker (optional, for full-stack testing)
- A [Groq API key](https://console.groq.com) (free tier available)

---

## Local setup

```bash
git clone https://github.com/k-satyam215/repomind-ai.git
cd repomind-ai
bash setup.sh
```

`setup.sh` creates a virtual environment, installs dependencies, copies `.env.example` → `.env`, and runs the test suite.

Add your `GROQ_API_KEY` to `.env` before starting any services.

---

## Running the stack locally

```bash
# Terminal 1 — Backend API
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — MCP Tool Server
uvicorn src.mcp.server:app --port 9000

# Terminal 3 — Streamlit UI
streamlit run frontend/app.py
```

Or with Docker:

```bash
docker-compose up --build
```

---

## Running tests

```bash
pytest tests/ -v --tb=short
```

All 70 tests must pass with 0 warnings before submitting a PR. No API key is needed — all LLM calls are mocked.

```
tests/test_tools.py          24 passed  ✅
tests/test_agents.py         17 passed  ✅
tests/test_api.py            12 passed  ✅
tests/test_observability.py  17 passed  ✅
70 passed — 0 warnings
```

---

## Code style

RepoMind uses [Ruff](https://github.com/astral-sh/ruff) for linting:

```bash
pip install ruff
ruff check src/ backend/ frontend/ --select E,F,W,I
```

CI will fail if Ruff reports any errors.

---

## Submitting a pull request

1. Fork the repo and create a branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes. Add or update tests as needed.

3. Ensure all 70 tests pass and Ruff is clean.

4. Open a PR against `main` with a clear description of what changed and why.

---

## Project structure

See the [README](README.md#project-structure) for a full directory breakdown.

---

## Reporting bugs

Open a [GitHub Issue](https://github.com/k-satyam215/repomind-ai/issues) with:
- A minimal reproducible example
- The repo URL you were analyzing (if applicable)
- The error output or unexpected behavior

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
