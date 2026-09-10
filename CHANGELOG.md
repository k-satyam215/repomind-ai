# Changelog

All notable changes to **RepoMind AI** are documented here.

## [1.6.0] — Private Repo Support & Subprocess Hardening

### Added
- `analyze_repository()` accepts an optional `github_token` (GitHub PAT), falling back to
  the `GITHUB_TOKEN` env var, enabling analysis of **private repositories**.
- `RepoRequest` / `ParallelAnalyzeRequest` API models expose the same `github_token` field.
- `tests/test_security.py` — 13 tests covering authenticated clone URLs, token redaction,
  and end-to-end no-token-leak guarantees.

### Security
- Token is embedded in the clone URL **only** for the `git clone` call, is stripped from
  the clone's `.git/config` immediately after cloning succeeds
  (`strip_token_from_git_config`), and is scrubbed from any git error before it is logged
  or returned (`redact_token`) — GitPython's own exceptions embed the full authenticated
  command line.
- `fix_generator._run_in_subprocess` now runs LLM-generated code (self-heal / multi-file
  fix verification) with a minimal, secret-free environment allowlist instead of a full
  `os.environ.copy()` — `GROQ_API_KEY` / `GITHUB_TOKEN` can no longer reach a subprocess
  executing code derived from an untrusted repository.
- `_self_heal()` and `generate_multi_file_fix()` now correctly respect
  `RUN_RUNTIME_VALIDATION=false` — previously both executed generated code in a subprocess
  regardless of the flag, silently bypassing the operator's opt-out.

### Fixed
- `backend/main.py::health_detailed()` — simplified a fragile overall-status condition
  and replaced a hardcoded `/tmp` disk-usage check with `tempfile.gettempdir()`, which
  was silently misreporting free space on Windows.
- Version string (`1.0.0` / `1.2.0` / `1.5.0` across `pyproject.toml`, `backend/main.py`,
  and `frontend/app.py`) unified to a single value (see `APP_VERSION` in
  `backend/main.py`), removing drift between the API, UI, and package metadata.

Verified: full suite 137/137 tests passing.

## [1.5.0] — HuggingFace Spaces Deploy

### Added
- `.github/workflows/hf-deploy.yml` — tag-triggered (`v*.*.*`) CD pipeline that pushes an
  orphan branch (binary/media files stripped) to a HuggingFace Space.
- Live public demo on HuggingFace Spaces.

## [1.4.0] — Prompt-Injection Defense

### Added
- `src/core/prompt_guard.py` — pattern-based detection (modeled on Microsoft PyRIT's
  attack taxonomy) plus explicit `<untrusted_repository_code>` fencing, applied at every
  LLM call site that receives repository source (`bug_detector`, `fix_generator`).
- `SECURITY_INSTRUCTION` appended to the relevant system prompts, instructing the model to
  treat fenced repo content strictly as data, never as instructions.
- `tests/test_prompt_guard.py` covering direct overrides, DAN-style jailbreaks, system-
  prompt exfiltration attempts, and false-positive avoidance on ordinary admin-related code.

## [1.3.0] — Observability & Reliability

### Added
- `src/observability/metrics.py` — thread-safe run/fix/severity/retry/latency tracking,
  served at `GET /metrics`.
- Streamlit "Observability" tab — live metrics, integration status (Redis, LangSmith).
- Redis-backed analysis caching (`src/core/cache.py`) with in-memory-safe fallback when
  Redis is unavailable.
- LangSmith tracing for every LLM call (latency, tokens, input/output).

### Fixed
- LangGraph node named `fix` collided with the `fix` state-machine channel, causing a
  graph-compile-time failure — node renamed to `generate_fix`.
- Redis cache-hit responses carried a stale `repo_path` from a previous process's temp
  directory, crashing the autonomous fix pipeline — the graph now forces a fresh clone
  (`force_refresh=True`) regardless of cache state.
- An unreadable file during the fix stage previously left `current_issue_index`
  unchanged, causing an infinite loop on the same issue — it now advances to the next
  issue like the max-retries path does.

## [1.2.0] — Multi-Issue & Multi-File Fixing

### Added
- Agent graph processes **all** detected issues in a repo, not just the first, each with
  an independent retry loop (`current_issue_index`, `issue_results`).
- `generate_multi_file_fix` / `apply_multi_file_patch` — fixes spanning multiple
  dependency-related files, applied atomically with backup + rollback.
- Async parallel issue processing (`process_issues_parallel`, semaphore-bounded) exposed
  via `POST /analyze/parallel`.
- SSE streaming endpoints: `/analyze/stream` (live progress) and `/fix/stream`
  (token-by-token fix generation).
- Human-in-the-loop approval flow — `/fix`, `/fix/multi`, and `/diff` only preview
  changes; `/fix/approve` is the sole endpoint that writes to a repo.

## [1.1.0] — Codex-Style Self-Healing & Sandboxed Execution

### Added
- Runtime verification loop in `fix_generator.py`: syntax check → optional subprocess
  execution → self-heal (LLM retries against the actual runtime error, up to 3 attempts).
- `src/tools/sandbox_patch.py` — every fix is applied to an isolated `shutil.copytree`
  copy of the repo; the original is only updated after pytest passes in the sandbox.
- ChromaDB-backed vector memory (`src/memory/vector_memory.py`) — past `(bug, fix)` pairs
  are retrieved as context for similar future bugs.
- Confidence + severity scoring on bug detections; detections below 0.6 confidence are
  discarded to reduce false positives.

## [1.0.0] — Initial Release

### Added
- Core LangGraph pipeline: analyze → fix → apply_patch → test → reflect → finalize.
- MCP tool server (`src/mcp/`) decoupling agent reasoning from filesystem/subprocess
  execution (`read_file`, `apply_patch`, `run_tests`).
- GitHub PR creation on successful fix (`src/integrations/github_pr_agent.py`).
- FastAPI backend + Streamlit frontend.
- Initial test suite and GitHub Actions CI.
