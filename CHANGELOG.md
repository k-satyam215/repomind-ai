@'
# Changelog

All notable changes to this project are documented here.

## [1.3.0] — Production Hardening, LLM Caching & Deployment Prep

### Added
- LLM response caching (`app/llm.py`) — identical (model, system, prompt, params) calls
  within `LLM_CACHE_TTL_SECONDS` (default 300s) skip the Groq network call entirely,
  backed by the same Redis/in-memory `Cache` used for the approval queue.
- Input validation on `POST /tasks` and `/tasks/batch` — `description` is bounded
  (non-empty, max length) and `repo` must match a strict `owner/repo` slug pattern,
  rejecting path-traversal-style values (e.g. `../secret`, `owner/..`) before they're
  ever used to build a GitHub API URL.
- `MAX_BATCH_SIZE` cap on `/tasks/batch` (422 if exceeded) and `MAX_CONCURRENT_TASKS`
  now clamped to a sane [1, 10] range — both defensive bounds against accidental or
  malicious oversized requests.
- Dashboard: a 5th top-line metric for pending approvals, and a dedicated "Security
  events — prompt injection flagged" section surfacing any `research.security` trace
  rows.
- Hugging Face Spaces Docker configuration that keeps the FastAPI API private and
  serves the Streamlit dashboard publicly.

### Fixed
- `POST /tasks/{id}/approve` previously returned `"executed": bool(approved)`, implying
  an approved action was actually carried out — no such execution step exists in the
  code. It now always returns `"executed": false` with a clear `authorization_status`
  field, so the API stops claiming to do something it doesn't.
- Repo-slug validation regex tightened to reject `.`/`..` path segments specifically
  (the original character-set-based pattern allowed `../secret` through since `.` was
  an allowed character).
- Network tool calls (GitHub, Slack) now use bounded timeouts instead of blocking
  indefinitely.
- Local Docker Compose no longer exposes the Redis port or binds the API to all
  interfaces by default — reduces accidental exposure in local/dev environments.
- `.gitignore` covers temporary pytest artifacts, lint caches, and accidental
  shell-output files.

## [1.2.0] — LLM Security Hardening

### Added
- `app/security.py`: pattern-based prompt-injection detection and `<untrusted_external_data>`
  fencing for content retrieved from external tools.
- Secret/credential leak scanning (`scan_for_secrets`) integrated into the Critic Agent —
  blocks any outbound action body resembling an API key, bearer token, or private key.
- 10 new tests covering both defenses, including a full `research_node` run against a
  simulated malicious GitHub issue body.
- `SECURITY.md` documenting the project's security scope and known limitations.

### Fixed
- Test-isolation bug: three `test_cache.py` tests expecting pure in-memory behaviour were
  inadvertently picking up the CI-level `REDIS_URL` environment variable (set so the
  separate real-Redis integration tests could run). Fixed with `monkeypatch.delenv` in the
  three affected tests.

## [1.1.0] — Reliability & Observability

### Added
- Redis-backed `ApprovalStore` with automatic in-memory fallback — pending approvals now
  survive process restarts and are shared across worker processes.
- `/tasks/batch` endpoint — semaphore-bounded concurrent processing of multiple tickets.
- `/metrics` endpoint — system-wide aggregate stats (success rate, per-node cost/latency).
- Optional LangSmith tracing via `@traceable` on LLM and tool calls.
- `benchmark.py` — reproducible benchmark script with 11 scenarios and self-validating
  expectation assertions.
- CI/CD: Redis service container in GitHub Actions, tag-triggered Docker Hub publish.

### Fixed
- Critic/approval action-type mismatch (`delete_resource` rejected as "unknown").
- Retry-exhausted tasks left at `in_progress` instead of `failed` — added explicit
  `mark_failed` terminal graph node.
- Two benchmark scenarios had incorrectly hand-calculated risk-score expectations,
  caught only once the benchmark's self-validation assertion was added.

## [1.0.0] — Initial Release

### Added
- Core LangGraph supervisor pattern: Triage, Research, Action, and Critic agents.
- Deterministic risk scoring and human-approval gate for high-risk actions.
- MCP-style tool layer (GitHub, Slack) with mock-mode fallback.
- FastAPI backend with SSE streaming for live task progress.
- Streamlit observability dashboard.
- SQLite-backed eval tracker (per-node latency, cost, pass/fail).
- Groq (free-tier) LLM integration.
- Initial test suite and GitHub Actions CI.