---
title: RepoMind AI
emoji: 🤖
colorFrom: indigo
colorTo: purple
sdk: docker
app_file: huggingface_app.py
pinned: false
---

<div align="center">

# RepoMind AI

### Review-first AI Repository Analysis

**Give it a GitHub URL. RepoMind maps the codebase, surfaces likely issues, and produces review-ready fix previews. Nothing is pushed to GitHub automatically.**

[![CI](https://github.com/k-satyam215/repomind-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/k-satyam215/repomind-ai/actions/workflows/ci.yml)
[![CD](https://github.com/k-satyam215/repomind-ai/actions/workflows/cd.yml/badge.svg)](https://github.com/k-satyam215/repomind-ai/actions/workflows/cd.yml)
[![HF Deploy](https://github.com/k-satyam215/repomind-ai/actions/workflows/hf-deploy.yml/badge.svg)](https://github.com/k-satyam215/repomind-ai/actions/workflows/hf-deploy.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent-FF6B35)](https://langchain-ai.github.io/langgraph)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![HuggingFace](https://img.shields.io/badge/🤗%20HuggingFace-Spaces-FFD21E)](https://huggingface.co/spaces/satyam215/repomind-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E)](LICENSE)

<br/>

<img src="assets/architecture.svg" alt="RepoMind AI Architecture" width="680"/>

<br/>

> RepoMind is a review-first repository agent: repo understanding → issue detection with confidence
> scoring → dependency-aware fix generation → diff preview → explicit user approval. The hosted
> experience is read-only with respect to GitHub: it never pushes commits or creates pull requests.

</div>

---

## What it does

RepoMind runs a stateful, multi-step agent graph (LangGraph) against public GitHub Python repositories,
or private repositories when a scoped read-only token is supplied:

1. **Clones and parses** the repository, building a dependency map from import analysis
2. **Prioritizes files** by structural importance (entry points, config, core modules)
3. **Detects bugs** via LLM with confidence and severity scoring — low-confidence detections are filtered out
4. **Generates fixes** with full dependency context — related files are injected into the prompt, and past similar fixes from vector memory (ChromaDB) are retrieved and included
5. **Validates** every fix with AST syntax checking before it touches any file
6. **Applies patches** atomically to an isolated sandbox copy — original repo is never modified until tests pass
7. **Runs pytest** on the sandboxed repo via the MCP tool layer
8. **Reflects** on test failures and retries with a revised strategy (up to 3 cycles) — or stops if the planner determines the bug is unfixable
9. **Processes all detected issues** — not just the first one; each issue has its own retry loop
10. **Shows a reviewable diff** and waits for explicit user approval before applying a preview to the
    temporary analysis workspace
11. **Records metrics** — fix success rate, retry distribution, stage latency, severity breakdown — served at `/metrics`

## Private repositories and safe review

RepoMind supports private repositories through a fine-grained GitHub personal access token (PAT).
Use the smallest possible permission set:

1. In GitHub, create a **fine-grained** token with access to **only the repository** you intend to analyze.
2. Grant **Repository contents: Read-only**. GitHub adds **Metadata: Read-only** automatically.
3. In RepoMind, enter the HTTPS repository URL and paste the token into the masked **GitHub personal
   access token (optional)** field.
4. Review every finding and diff. Run the target repository's test suite before using any suggested fix.
5. Revoke short-lived test tokens when the test is complete.

Token-authorised analyses bypass the shared cache. The token is used only to authenticate cloning and is
redacted from errors and logs. Do not grant write permissions for the current hosted workflow.

### What “Approve & Apply” means

In the current UI, approval writes the reviewed preview only to RepoMind's temporary cloned workspace.
It does **not** commit, push, or open a pull request on GitHub. Copy the reviewed change into your branch,
run your own tests, then commit and push through your normal Git workflow. A future PR integration should
use an explicit approval screen, a new branch, least-privilege write access, and passing tests—not direct
pushes to `main`.

---

## Architecture

| Layer | Technology | Role |
|---|---|---|
| Frontend | Streamlit | User input, live SSE progress streaming, per-issue fix generation |
| Backend API | FastAPI | `/analyze` `/fix` `/diff` `/metrics` — orchestrates the pipeline |
| Agent Graph | LangGraph | Stateful loop: analyze → fix → patch → test → reflect → retry |
| MCP Tool Layer | FastAPI (port 9000) | Isolated tool execution: `read_file`, `apply_patch`, `run_tests` |
| Memory | ChromaDB + Redis | Vector memory for cross-session fix reuse; Redis for analysis caching + history |
| Tracing | LangSmith | Every LLM call traced — latency, tokens, input/output visible in dashboard |
| Observability | Custom metrics module | Fix rates, retry distribution, stage latency, severity breakdown |
| CI/CD | GitHub Actions | Lint + test + Docker build on every push; Docker Hub publish on tag |
| Deployment | Docker Compose | 4 services: Redis (6379), backend (8000), MCP server (9000), frontend (8501) |

---

## Key design decisions

**Why MCP as the tool layer?**
The Model Context Protocol decouples agent reasoning from tool execution. Each tool (`read_file`, `apply_patch`, `run_tests`) is a separate HTTP endpoint on an isolated service. Agent logic never directly touches the filesystem or subprocess — it calls the MCP server, which is sandboxed and independently testable.

**Why a sandbox copy, not in-place patching?**
The original cloned repo is never modified until all tests pass. Every fix is applied to a `shutil.copytree` copy (excluding `.git`). If tests fail, the sandbox is deleted. If they pass, the sandbox is committed back to the original. This means a failed fix leaves zero artifacts.

**Why confidence scoring in bug detection?**
Early versions had a high false-positive rate — the LLM would flag style issues as bugs. Adding explicit `confidence` (0.0–1.0) and `severity` (critical/high/medium) fields to the detection schema, and filtering detections below 0.6 confidence, reduced false positives significantly in benchmarks.

**Why process all issues, not just the first?**
Single-issue fixing is a demo-level feature. Production agents must handle multiple independent bugs in the same repo. Each issue gets its own retry loop with independent state; the graph advances `current_issue_index` after each success or max-retry exhaustion.

---

## Benchmark

Run against real-world open-source Python repositories using the included benchmark runner:

```bash
python benchmark.py --output results.json
```

| Repository size | Files analyzed | Bugs detected | Fix success rate |
|---|---|---|---|
| Small (~10 files) | 10 | 3 | **100%** |
| Medium (~40 files) | 30 | 7 | **71%** |
| Large (~100 files) | 30 | 12 | **58%** |

Fix success rate is defined as: fixes that passed `pytest` in the sandboxed repo / total fix attempts.
Benchmarks are reproducible — see `benchmark.py` for the exact repos and methodology.

---

## Observability

A live metrics endpoint is exposed at `GET /metrics`:

```json
{
  "total_runs": 12,
  "total_bugs_detected": 34,
  "total_fixes_succeeded": 22,
  "fix_success_rate_pct": 64.7,
  "severity_distribution": { "critical": 8, "high": 14, "medium": 12 },
  "retry_distribution": { "0": 14, "1": 5, "2": 2, "3": 1 },
  "avg_stage_latency_ms": {
    "clone": 4200,
    "detect": 1800,
    "fix_generate": 2100,
    "test_run": 8500
  },
  "recent_runs": [...]
}
```

---

## Tests

```bash
pytest tests/ -v
```

```
138 passed (latest local verification)
```

The suite covers agents, graph integration, API routes, observability, prompt safety,
token handling and sandbox tools. LLM and Git calls are mocked where appropriate so
unit tests are fast and repeatable.

---

## Quick start

### Local

```bash
git clone https://github.com/k-satyam215/repomind-ai.git
cd repomind-ai
bash setup.sh
```

```env
# .env
GROQ_API_KEY=your_groq_api_key_here
GITHUB_TOKEN=your_github_token_here    # optional — private-repo clone token; use read-only scope
```

```bash
# Terminal 1
uvicorn backend.main:app --reload --port 8000

# Terminal 2
uvicorn src.mcp.server:app --port 9000

# Terminal 3
streamlit run frontend/app.py
```

Open **http://localhost:8501** → paste a GitHub repo URL → click **Analyze**.

### Docker

```bash
cp .env.example .env
# Add GROQ_API_KEY to .env
docker-compose up --build
```

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI backend | http://localhost:8000 |
| MCP tool server | http://localhost:9000 |
| Swagger docs | http://localhost:8000/docs |
| Live metrics | http://localhost:8000/metrics |

```bash
docker pull satyam215/repomind-ai:latest
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Get free at [console.groq.com](https://console.groq.com) |
| `GITHUB_TOKEN` | No | — | GitHub fine-grained PAT for private-repository cloning; use repository contents read-only |
| `GROQ_MODEL_STRONG` | No | `openai/gpt-oss-120b` | Model for bug detection, fix generation, repo analysis |
| `GROQ_MODEL_FAST` | No | `openai/gpt-oss-20b` | Model for reflection + retry/stop planning |
| `LANGSMITH_API_KEY` | No | — | [LangSmith](https://smith.langchain.com) API key — enables full LLM call tracing |
| `LANGSMITH_PROJECT` | No | `repomind-ai` | LangSmith project name |
| `LANGSMITH_TRACING` | No | `true` | Enable/disable tracing when key is set |
| `REDIS_URL` | No | — | Redis URL — enables analysis caching + persistent memory ([Upstash](https://upstash.com) free tier works) |
| `REDIS_CACHE_TTL` | No | `3600` | Cache TTL in seconds (default 1 hour) |
| `MCP_URL` | No | `http://localhost:9000/tool` | MCP tool server endpoint |
| `BACKEND_URL` | No | `http://localhost:8000` | Backend URL used by Streamlit |
| `MAX_ANALYSIS_FILES` | No | `30` | Max files to run bug detection on |
| `MAX_FIX_LINES` | No | `150` | Max lines in a generated fix |
| `MAX_RETRIES` | No | `3` | Max retries per bug in the reflection loop |
| `TEST_TIMEOUT` | No | `300` | pytest timeout in seconds |

---

## Project structure

```
repomind-ai/
├── backend/
│   └── main.py                    FastAPI entry point
├── frontend/
│   └── app.py                     Streamlit UI
├── src/
│   ├── agents/
│   │   ├── bug_detector.py        LLM bug detection with confidence + severity scoring
│   │   ├── fix_generator.py       Full-file fix generation with context injection
│   │   ├── multi_file_patch_agent.py Multi-file fix orchestration
│   │   ├── parallel_processor.py  Bounded-concurrency issue processing
│   │   ├── patch_apply_agent.py   Atomic write + .bak backup + rollback
│   │   ├── planner_agent.py       Retry / stop decision
│   │   ├── reflection_agent.py    Failure analysis
│   │   ├── repo_analyzer.py       Repository structure and dependency analysis
│   │   └── test_runner_agent.py   Pytest via subprocess
│   ├── graph/
│   │   └── agent_graph.py         LangGraph state machine — multi-issue loop
│   ├── mcp/
│   │   ├── server.py              MCP tool server
│   │   ├── client.py              MCP client with timeout + error handling
│   │   └── registry.py            Tool registry
│   ├── memory/
│   │   ├── simple_memory.py       Thread-safe JSON key-value store
│   │   └── vector_memory.py       ChromaDB PersistentClient
│   ├── observability/
│   │   └── metrics.py             Fix rates, latency, severity breakdown, /metrics endpoint
│   ├── tools/
│   │   ├── ast_validator.py       Python syntax validation
│   │   ├── dependency_graph.py    Import-based dependency map
│   │   ├── diff_tools.py          Unified diff generation
│   │   ├── file_prioritizer.py    File scoring and ranking
│   │   ├── file_tools.py          Safe file read
│   │   └── sandbox_patch.py       Isolated sandbox copy
│   ├── integrations/
│   │   └── github_pr_agent.py     Internal PR integration; not used by hosted UI
│   ├── api/
│   │   └── routes.py              Analyze, stream, diff, approval, multi-file and metrics routes
│   ├── core/
│   │   ├── cache.py               Redis-backed analysis cache
│   │   ├── config.py              Environment configuration
│   │   ├── logger.py              Structured logging
│   │   ├── prompt_guard.py        Untrusted repository-code prompt boundary
│   │   └── security.py            Token redaction and managed path protection
│   └── utils/
│       ├── repo_parser.py         Recursive file walker
│       └── repo_filter.py         Python-only path filter
├── tests/
│   ├── test_agent_graph.py        Graph construction and routing tests
│   ├── test_agents.py             Agent unit tests
│   ├── test_api.py                FastAPI route tests
│   ├── test_graph_integration.py  End-to-end graph integration tests
│   ├── test_observability.py      Metrics and timing tests
│   ├── test_prompt_guard.py       Prompt-injection boundary tests
│   ├── test_security.py           Token and path-safety tests
│   └── test_tools.py              AST, diff, file and sandbox tests
├── benchmark.py                   Reproducible benchmark runner
├── docker-compose.yml             4-service deployment (Redis, backend, MCP, frontend)
├── Dockerfile
├── pyproject.toml
├── setup.sh
└── .env.example
```

---

## Roadmap

- [x] Parallel multi-issue processing (async + Semaphore-bounded concurrency)
- [x] Streaming fix generation (SSE token-by-token)
- [x] Live SSE progress streaming during analysis (clone → parse → detect → complete)
- [x] Multi-file fix with dependency context
- [x] Human-in-the-loop approve/reject before applying fixes
- [x] Live observability dashboard (Streamlit Observability tab)
- [x] LangSmith tracing — every LLM call traced with latency + token counts
- [x] Redis caching — same repo analyzed once, instant results after (Upstash)
- [x] Codex-style runtime verification + self-heal loop (fix → run → fix error → repeat)
- [x] Docker Hub publish on version tag (CD pipeline)
- [x] HuggingFace Spaces live demo deploy
- [x] Private repository analysis with a masked, read-only fine-grained PAT field
- [x] Token-authorised runs bypass the shared repository-analysis cache
- [ ] JavaScript / TypeScript support
- [ ] Cloud sandbox execution (E2B / Modal) — no local Docker dependency
- [ ] Slack / Discord notification on fix completion
- [ ] Approval-gated GitHub Pull Request creation on a dedicated branch

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and guidelines.
See [AGENTS.md](AGENTS.md) to understand how the agent graph works before making changes.

```bash
git checkout -b feature/your-feature
pytest tests/ -v        # latest verified suite: 138 passed
git push origin feature/your-feature
# open a Pull Request
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built by [Satyam Kumar](https://github.com/k-satyam215)**

[GitHub](https://github.com/k-satyam215) · [LinkedIn](https://www.linkedin.com/in/satyam-kumar-266b38254)

</div>
