# AGENTS.md

> This file describes how RepoMind AI's autonomous agent works — what it does, how it makes
> decisions, what tools it can use, and what constraints it operates under.
> Intended for developers contributing to the agent, and for AI coding assistants that need
> to understand the project structure before making changes.

---

## What the agent does

RepoMind is a **fully autonomous software engineering agent**. Given a public GitHub Python
repository URL, it runs the following loop without human intervention:

```
Clone repo
    ↓
Parse structure + build dependency graph
    ↓
Prioritize files by structural importance
    ↓
Detect bugs (LLM, confidence + severity scored)
    ↓  [for each bug]
Generate fix (with dependency context + vector memory)
    ↓
Validate fix (AST syntax check)
    ↓
Apply to sandbox copy (never touch original)
    ↓
Run pytest in sandbox
    ↓
On failure: reflect → plan → retry (up to 3 cycles)
    ↓
On success: commit sandbox → original, open GitHub PR
    ↓
Record metrics
    ↓
Advance to next bug
```

The agent processes **all detected issues**, not just the first. Each issue has its own
independent retry loop with shared observability.

---

## Agent graph (`src/graph/agent_graph.py`)

Built with **LangGraph** (`StateGraph`). Nodes and their responsibilities:

| Node | What it does |
|---|---|
| `analysis` | Clones repo, builds dep map, detects all bugs, records run start |
| `fix` | Reads main + related files, queries vector memory, generates fix, validates AST |
| `apply_patch` | Creates sandbox copy, applies fix to sandbox via MCP |
| `test` | Runs pytest on sandbox via MCP |
| `reflect` | Evaluates result; on success: commits + creates PR; on failure: reflects + plans |
| `finalize` | Records run summary metrics, cleans up |

### State keys

```python
class AgentState(TypedDict, total=False):
    repo_url: str                  # input
    repo_data: dict                # clone result + issues + dep_map
    current_issue_index: int       # which bug we're on
    issue_results: list[dict]      # [{file, success, retries, pr_url, severity}]
    fix: str                       # current generated fix
    test_result: dict              # {success, output}
    retry_count: int               # retries for current issue
    reflection: str                # failure analysis from reflect node
    action: str                    # "retry" | "next_issue" | "stop"
    current_file: str
    original_code: str
    sandbox_repo: str              # path to sandbox copy
    patch_status: dict
    run_id: str
    run_start_ms: float
```

### Conditional edge logic

After `reflect`, the graph branches on `state["action"]`:
- `"retry"` → back to `fix` (same issue, new attempt)
- `"next_issue"` → back to `fix` (incremented `current_issue_index`, reset `retry_count`)
- `"stop"` or `"done"` → `finalize`

---

## Tools (`src/mcp/`)

Tools are exposed as HTTP endpoints on the **MCP server** (port 9000). The agent never
directly touches the filesystem — it calls the MCP server, which is sandboxed.

| Tool | Endpoint | Args | Returns |
|---|---|---|---|
| `read_file` | `POST /tool` | `{tool: "read_file", args: {path}}` | `{output: str}` |
| `apply_patch` | `POST /tool` | `{tool: "apply_patch", args: {repo_path, file, code}}` | `{success, error?}` |
| `run_tests` | `POST /tool` | `{tool: "run_tests", args: {repo_path}}` | `{success, output}` |

The MCP client (`src/mcp/client.py`) handles timeout and error wrapping.

### Why MCP?

The Model Context Protocol decouples agent reasoning from execution. Tool logic is independently
testable and replaceable without touching agent code. The MCP server can be swapped for a
remote sandboxed service (E2B, Modal) without changing the agent.

---

## Memory (`src/memory/`)

Two memory systems run in parallel:

**Vector memory** (`vector_memory.py` — ChromaDB):
- Stores past `(bug, fix)` pairs as embeddings
- Retrieved at fix-generation time via `search_similar_bug(bug_report)`
- Improves fix quality for recurring bug patterns across sessions

**Key-value memory** (`simple_memory.py` — JSON):
- Thread-safe JSON store at `./repomind_memory/memory.json`
- Stores full run records for debugging and audit

---

## Bug detection schema

`detect_bugs()` returns a structured dict or `None`:

```python
{
    "bug": str,           # human-readable description
    "impact": str,        # what breaks
    "fix_hint": str,      # how to fix
    "severity": "critical" | "high" | "medium",
    "confidence": float,  # 0.0–1.0; detections below 0.6 are discarded
    "bug_type": "import_error" | "runtime_error" | "logic_error" |
                "deprecated_api" | "type_error" | "other"
}
```

Detections with `confidence < 0.6` are silently dropped to reduce false positives.

---

## Observability (`src/observability/metrics.py`)

All agent activity is recorded to `./repomind_memory/metrics.json` (thread-safe, JSON).

Tracked:
- `total_runs`, `total_bugs_detected`, `total_fixes_succeeded`, `total_fixes_failed`
- `retry_distribution` — how many fixes needed 0/1/2/3 retries
- `severity_distribution` — critical/high/medium counts
- `avg_stage_latency_ms` — per-stage timing
- `fix_success_by_severity` — success rate broken down by severity
- `recent_runs` — last 20 run summaries

Live at `GET /metrics` on the backend.

---

## Sandbox design

**The original cloned repo is NEVER modified until all tests pass.**

1. `create_sandbox_copy(repo_path)` — `shutil.copytree` excluding `.git`
2. All patches applied to sandbox
3. pytest runs on sandbox
4. On success: `commit_sandbox_changes(sandbox, original)` — copies sandbox back
5. On failure or exception: sandbox deleted in `reflect` node's `finally` block

This guarantees zero artifacts from failed fix attempts.

---

## Human-in-the-loop API mode

The backend also exposes a human-approval workflow for interactive use:

```
POST /analyze          → returns issues + repo_path (no changes made)
POST /fix              → returns {old, new} (no changes made)
POST /diff             → returns unified diff for preview
POST /fix/approve      → APPLIES fixes only after user approval
POST /fix/stream       → streams fix token-by-token (SSE)
POST /fix/multi        → multi-file fix with per-file diffs for preview
POST /analyze/parallel → detect + fix all issues in parallel, return previews
```

The autonomous graph mode (via `benchmark.py` or direct `build_graph().invoke(...)`) runs
without human confirmation.

---

## Adding a new tool

1. Add the tool function in `src/tools/` or `src/agents/`
2. Register it in `src/mcp/registry.py`
3. Add dispatch logic in `src/mcp/server.py`
4. Call it from agent nodes via `mcp_call("tool_name", {...})`
5. Add tests in `tests/test_tools.py`

---

## Adding a new agent node

1. Write the node function in `src/graph/agent_graph.py` — signature: `(state: AgentState) -> dict`
2. Return only the keys you want to update in state
3. Add the node: `graph.add_node("name", node_fn)`
4. Wire edges: `graph.add_edge(...)` or `graph.add_conditional_edges(...)`
5. Update this file

---

## Running the agent

```bash
# Full autonomous run on a repo
python -c "
from src.graph.agent_graph import build_graph
g = build_graph()
result = g.invoke({'repo_url': 'https://github.com/owner/repo'})
print(result['issue_results'])
"

# Benchmark suite
python benchmark.py --output results.json

# Single repo benchmark
python benchmark.py --repo https://github.com/owner/repo
```

---

## Constraints the agent operates under

- Only analyzes **Python** files (`.py`). JavaScript/TypeScript support is on the roadmap.
- Maximum `MAX_ANALYSIS_FILES` (default 30) files per repo for bug detection.
- Maximum `MAX_FIX_LINES` (default 150) lines per generated fix — larger fixes are rejected.
- Maximum `MAX_RETRIES` (default 3) retry cycles per bug before moving to next issue.
- `TEST_TIMEOUT` (default 300s) — pytest timeout per run.
- Bug detections with `confidence < 0.6` are discarded before reaching the fix stage.
- PR creation requires `GITHUB_TOKEN` env var — optional, agent proceeds without it.
- The agent never force-pushes to `main` — creates a new branch for every PR.
