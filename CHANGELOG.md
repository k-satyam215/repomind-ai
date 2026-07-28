# Changelog

All notable changes to RepoMind AI are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.4.1] — 2026-07-28

### Fixed
- **Dependency versions updated** to resolve `HTTPConnectionPool Read timed out` error.
  Root cause: `langchain-groq==0.1.3` does not support `openai/gpt-oss-*` model names
  introduced by Groq's June 2026 migration, causing all LLM calls to fail silently
  and the backend to hang until the 300s frontend timeout.
  - `langchain-groq` bumped to `>=0.2.0,<0.3` (supports new model names)
  - `langchain` / `langchain-core` bumped to `>=0.3.0,<0.4` (required by langchain-groq 0.2)
  - `langgraph` bumped to `>=0.2.0,<0.4` (was `0.0.48`, breaking API changes)
  - `uvicorn` bumped to `>=0.30,<0.35` + `[standard]` extras for better async performance
  - `fastapi` bumped to `>=0.115,<0.116`
- **Frontend timeout increased** from 300s to 600s to handle large repo clones.
- **Better error messages** in Streamlit: timeout vs connection refused are now
  shown as separate, actionable error messages.
- **Backend start command** updated: `--timeout-keep-alive 600` added to uvicorn
  invocation in `setup.sh` and `docker-compose.yml`.
- **`uv.lock` should be regenerated** after this update: `uv lock` or delete the
  old lock file and run `pip install -r requirements.txt` fresh.

---

## [1.4.0] — 2026-07-05

### Changed
- **Migrated off deprecated Groq models.** `llama-3.3-70b-versatile` (used across
  `bug_detector.py`, `fix_generator.py`, `repo_analyzer.py`, `reflection_agent.py`,
  `planner_agent.py`) was deprecated by Groq on 2026-06-17. Replaced with Groq's
  recommended successors, now configurable via env vars instead of hardcoded:
  - `GROQ_MODEL_STRONG` (default `openai/gpt-oss-120b`) — bug detection, fix
    generation, and repo structure analysis, where output quality matters most.
  - `GROQ_MODEL_FAST` (default `openai/gpt-oss-20b`) — reflection summaries and
    the binary retry/stop planner decision, where a smaller model is sufficient
    and reduces retry-loop latency and cost.
- `src/core/config.py` now exposes `GROQ_MODEL_STRONG` / `GROQ_MODEL_FAST` so
  future model swaps require no code changes, only an env var update.
- `.env.example` and `README.md` updated with the new model env vars.

---

## [1.3.0] — 2025-06-12

### Added
- `AGENTS.md` — comprehensive agent architecture reference for contributors and AI coding tools
- `huggingface_app.py` — single-process entry point for HuggingFace Spaces deployment
- `.github/workflows/hf-deploy.yml` — auto-deploy to HF Spaces on version tags
- `GET /health/detailed` — deep health check verifying MCP reachability, disk space, memory dir, API key
- HuggingFace Spaces badge in README

### Fixed
- `apply_approved_fixes` return key mismatch: `changed_files` → `applied` (routes now consistent)
- Roadmap updated to reflect already-shipped features (parallel processing, streaming, HF deploy)

---

## [1.2.0] — 2025-01-15

### Added
- `src/observability/metrics.py` — thread-safe, JSON-persisted metrics tracker
- `GET /metrics` endpoint — live fix success rate, retry distribution, stage latency, severity breakdown
- Multi-issue parallel fixing — all detected bugs processed, each with its own retry loop
- Confidence scoring in `bug_detector.py` — detections below 0.6 confidence filtered as false positives
- `finalize_node` in agent graph — records run summary after all issues processed; total pipeline duration tracked
- `tests/test_observability.py` — 17 new unit tests (total: **70 tests, 0 warnings**)
- `benchmark.py` — reproducible benchmark runner with `--repo` and `--output` flags
- `benchmark_results.json` — benchmark results on 3 real open-source Python repos
- `CONTRIBUTING.md` — setup, test, and PR contribution guide
- `.github/workflows/cd.yml` — Docker Hub publish on version tag (`v*.*.*`)
- Streamlit Observability tab — live metrics dashboard with severity badges and recent run history
- `bug_type` field in detection schema — classifies bugs as `import_error` / `runtime_error` / `logic_error` / `deprecated_api` / `type_error` / `other`
- Architecture diagram updated (SVG) to reflect all new components

### Changed
- `backend/main.py` — version bump `1.0.0` → `1.2.0`
- `frontend/app.py` — severity + confidence badges on each issue, Observability metrics tab added
- `agent_graph.py` — multi-issue loop with `current_issue_index`, `issue_results`, full metrics integration
- `api/routes.py` — added `/metrics` route; test count updated from 9 → 12 in `test_api.py`
- `bug_detector.py` — detection schema extended with confidence + severity + bug_type fields
- `ci.yml` — added test artifact upload step, updated test count annotation
- README — architecture diagram + updated test counts + benchmark table + `/metrics` example

### Fixed
- `agent_graph.py` conditional edge — added `"next"` alias for planner compatibility
- Sandbox always cleaned up in `reflection_node` via `finally` block (no leaks on exception)
- `reflection_node` now records fix result metrics and advances to next issue on success or max-retry exhaustion

---

## [1.1.0] — 2024-12-20

### Added
- MCP tool layer as dedicated execution service (port 9000)
- ChromaDB persistent vector memory for cross-session fix reuse
- AST syntax validation before any patch is applied
- Atomic patch application with `.bak` backup + rollback on failure
- Sandbox copy execution — original repo untouched until tests pass
- `reflect_on_failure` + `plan_next_step` agents for retry strategy
- GitHub PR creation — no duplicates, no force push to default branch
- Docker Compose 3-service deployment
- GitHub Actions CI/CD: lint + test + Docker build on every push
- 50 tests, 0 warnings

### Changed
- Switched from synchronous subprocess blocking to `subprocess.run` to avoid asyncio event loop conflicts with FastAPI + LangGraph

---

## [1.0.0] — 2024-12-01

### Added
- Initial release
- LangGraph stateful agent graph: analyze → fix → patch → test → reflect
- Groq `llama-3.3-70b-versatile` as LLM backbone
- FastAPI backend with `/analyze`, `/fix`, `/diff`
- Streamlit frontend
- File prioritization by importance scoring
- Dependency graph from import analysis
