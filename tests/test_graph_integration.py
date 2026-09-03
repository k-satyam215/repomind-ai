"""
Integration tests for src/graph/agent_graph.py -- the orchestration layer
that had ZERO test coverage before this file. Individual agents were
tested in isolation (test_agents.py), but the graph WIRING itself --
how nodes route to each other -- was never exercised end to end.

These tests specifically prove three bugs found during a manual code
review are fixed, and guard against regression:

1. analysis_node now forces a fresh clone (force_refresh=True) instead of
   serving a cached analysis whose repo_path is None -- a cache hit would
   otherwise crash apply_patch_node with a missing/invalid repo_path.
2. fix_node's "could not read main file" branch now advances
   current_issue_index (mirroring the max-retries branch) instead of
   looping on the same unreadable file forever.
3. The "fix" -> "apply_patch" graph edge is now conditional on fix_node's
   own "action" field, so retry/next_issue/stop paths never reach
   apply_patch_node with a missing state["current_file"]/state["fix"].

All external calls (LLM, MCP HTTP server, GitHub, vector memory) are
mocked -- these tests exercise real graph routing logic, not real
network/subprocess calls, matching the mocking style already used in
test_agents.py.
"""
import pytest

from src.graph import agent_graph
from src.graph.agent_graph import build_graph, fix_node


def _base_repo_data(issues):
    return {
        "repo_path": "/fake/repo",
        "repo_url": "https://github.com/org/app",
        "dependency_map": {},
        "issues": issues,
    }


def _issue(file="app.py", severity="high", bug_type="logic"):
    return {"file": file, "report": {"severity": severity, "bug_type": bug_type}}


# ─── build_graph() wiring sanity ───────────────────────────────────────────

def test_build_graph_compiles():
    """
    Cheap but valuable: catches node-name typos, missing edges, or
    conditional-edge target keys that don't match any registered node --
    all of which raise at compile time, not at run time.
    """
    graph = build_graph()
    assert graph is not None


# ─── Fix #1: analysis_node bypasses the cache ──────────────────────────────

def test_analysis_node_forces_fresh_clone_bypassing_cache(monkeypatch):
    calls = {}

    def fake_analyze_repository(repo_url, force_refresh=False):
        calls["repo_url"] = repo_url
        calls["force_refresh"] = force_refresh
        return _base_repo_data([])

    monkeypatch.setattr(agent_graph, "analyze_repository", fake_analyze_repository)
    monkeypatch.setattr(agent_graph, "record_run_start", lambda: "run-1")
    monkeypatch.setattr(agent_graph, "record_bug_detected", lambda **kw: None)

    result = agent_graph.analysis_node({"repo_url": "https://github.com/org/app"})

    assert calls["force_refresh"] is True, (
        "analysis_node must pass force_refresh=True -- otherwise a cache hit "
        "returns repo_path=None and the fix pipeline crashes downstream."
    )
    assert result["repo_data"]["issues"] == []
    assert result["current_issue_index"] == 0


# ─── Fix #2: unreadable main file advances instead of looping ─────────────

def test_fix_node_unreadable_file_advances_and_does_not_loop(monkeypatch):
    state = {
        "repo_data": _base_repo_data([_issue("broken.py")]),
        "current_issue_index": 0,
        "issue_results": [],
        "retry_count": 0,
    }

    # Simulate an unreadable file: mcp_call("read_file", ...) returns no output.
    monkeypatch.setattr(agent_graph, "mcp_call", lambda tool, args: {"output": ""})
    monkeypatch.setattr(agent_graph, "get_related_files", lambda f, dep_map: [])

    result = fix_node(state)

    # Must NOT return the old bare {"action": "next_issue"} with no index
    # advance -- that looped forever on the same file.
    assert result["current_issue_index"] == 1, (
        "current_issue_index must advance past the unreadable file, or "
        "routing 'next_issue' back to 'fix' re-reads the SAME file forever."
    )
    assert result["action"] == "stop"  # only 1 issue total -> nothing left
    assert result["issue_results"][0]["file"] == "broken.py"
    assert result["issue_results"][0]["success"] is False


def test_fix_node_unreadable_file_with_more_issues_returns_next_issue(monkeypatch):
    state = {
        "repo_data": _base_repo_data([_issue("broken.py"), _issue("other.py")]),
        "current_issue_index": 0,
        "issue_results": [],
        "retry_count": 0,
    }
    monkeypatch.setattr(agent_graph, "mcp_call", lambda tool, args: {"output": ""})
    monkeypatch.setattr(agent_graph, "get_related_files", lambda f, dep_map: [])

    result = fix_node(state)

    assert result["current_issue_index"] == 1
    assert result["action"] == "next_issue"  # more issues remain -> keep going


# ─── Fix #3: full-graph routing never reaches apply_patch prematurely ─────

class _GraphMocks:
    """Bundles every external call the full graph makes, with call counters."""

    def __init__(self, monkeypatch, repo_data, fix_sequence, apply_patch_result=None,
                 test_result=None):
        self.apply_patch_calls = 0
        self.read_file_calls = 0
        self.pr_created = False
        self._fix_sequence = iter(fix_sequence)
        apply_patch_result = apply_patch_result or {"success": True}
        test_result = test_result or {"success": True, "output": "1 passed"}

        def fake_analyze_repository(repo_url, force_refresh=False):
            return repo_data

        def fake_mcp_call(tool, args):
            if tool == "read_file":
                self.read_file_calls += 1
                return {"output": "def broken():\n    return 1 / 0\n"}
            if tool == "apply_patch":
                self.apply_patch_calls += 1
                return apply_patch_result
            if tool == "run_tests":
                return test_result
            raise ValueError(f"Unexpected tool: {tool}")

        def fake_generate_fix(file, context, report, repo_path):
            return next(self._fix_sequence)

        def fake_create_fix_pr(repo_url, repo_path, fix):
            self.pr_created = True
            return {"success": True, "pr_url": "https://github.com/org/app/pull/1"}

        monkeypatch.setattr(agent_graph, "analyze_repository", fake_analyze_repository)
        monkeypatch.setattr(agent_graph, "mcp_call", fake_mcp_call)
        monkeypatch.setattr(agent_graph, "get_related_files", lambda f, dep_map: [])
        monkeypatch.setattr(agent_graph, "generate_fix", fake_generate_fix)
        monkeypatch.setattr(agent_graph, "search_similar_bug", lambda report: None)
        monkeypatch.setattr(agent_graph, "create_sandbox_copy", lambda repo_path: "/fake/sandbox")
        monkeypatch.setattr(agent_graph, "commit_sandbox_changes", lambda sandbox, original: None)
        monkeypatch.setattr(agent_graph, "save_vector_memory", lambda issue, fix: None)
        monkeypatch.setattr(agent_graph, "save_memory", lambda record: None)
        monkeypatch.setattr(agent_graph, "create_fix_pr", fake_create_fix_pr)
        monkeypatch.setattr(agent_graph, "record_run_start", lambda: "run-1")
        monkeypatch.setattr(agent_graph, "record_bug_detected", lambda **kw: None)
        monkeypatch.setattr(agent_graph, "record_fix_result", lambda **kw: None)
        monkeypatch.setattr(agent_graph, "record_pr_created", lambda: None)
        monkeypatch.setattr(agent_graph, "record_run_summary", lambda **kw: None)
        monkeypatch.setattr(agent_graph, "record_stage_latency", lambda *a: None)


def test_graph_full_happy_path_creates_pr_and_calls_apply_patch_once(monkeypatch):
    repo_data = _base_repo_data([_issue("app.py")])
    mocks = _GraphMocks(monkeypatch, repo_data, fix_sequence=["def fixed():\n    return 42\n"])

    graph = build_graph()
    final_state = graph.invoke({"repo_url": "https://github.com/org/app"})

    assert mocks.apply_patch_calls == 1
    assert mocks.pr_created is True
    assert final_state["issue_results"] == [{
        "file": "app.py",
        "success": True,
        "retries": 0,
        "pr_url": "https://github.com/org/app/pull/1",
        "severity": "high",
    }]


def test_graph_retry_then_success_only_calls_apply_patch_once(monkeypatch):
    """
    The critical regression test for the routing bug: generate_fix first
    returns code IDENTICAL to the original (triggering fix_node's "retry"
    action), then a genuinely different fix on the second attempt.

    Before the routing fix, EVERY return from fix_node (including the
    "retry" early-return with no state["current_file"]/state["fix"] set)
    flowed unconditionally into apply_patch_node, which would KeyError.
    With the fix, apply_patch_node must only run once -- on the second,
    successful attempt.
    """
    original_code = "def broken():\n    return 1 / 0\n"
    repo_data = _base_repo_data([_issue("app.py")])
    mocks = _GraphMocks(
        monkeypatch, repo_data,
        fix_sequence=[original_code, "def fixed():\n    return 42\n"],
    )

    graph = build_graph()
    final_state = graph.invoke({"repo_url": "https://github.com/org/app"})

    assert mocks.apply_patch_calls == 1, (
        "apply_patch must not be called on the 'no code change' retry attempt "
        "-- only once, after a genuinely different fix is generated."
    )
    assert final_state["issue_results"][0]["success"] is True
    assert final_state["issue_results"][0]["retries"] == 1


def test_graph_unreadable_first_issue_then_second_issue_succeeds(monkeypatch):
    """
    End-to-end proof combining fixes #2 and #3: issue 1's file is
    unreadable (mcp_call returns no output for read_file), issue 2
    succeeds normally. Before the fix, this would infinite-loop on
    issue 1 and never reach issue 2.
    """
    repo_data = _base_repo_data([_issue("missing.py"), _issue("app.py")])

    read_call_count = {"n": 0}

    def fake_mcp_call(tool, args):
        if tool == "read_file":
            read_call_count["n"] += 1
            # First read (issue 1, missing.py) fails; all subsequent reads succeed.
            if read_call_count["n"] == 1:
                return {"output": ""}
            return {"output": "def broken():\n    return 1 / 0\n"}
        if tool == "apply_patch":
            return {"success": True}
        if tool == "run_tests":
            return {"success": True, "output": "1 passed"}
        raise ValueError(tool)

    monkeypatch.setattr(agent_graph, "analyze_repository", lambda url, force_refresh=False: repo_data)
    monkeypatch.setattr(agent_graph, "mcp_call", fake_mcp_call)
    monkeypatch.setattr(agent_graph, "get_related_files", lambda f, dep_map: [])
    monkeypatch.setattr(agent_graph, "generate_fix", lambda *a: "def fixed():\n    return 42\n")
    monkeypatch.setattr(agent_graph, "search_similar_bug", lambda report: None)
    monkeypatch.setattr(agent_graph, "create_sandbox_copy", lambda repo_path: "/fake/sandbox")
    monkeypatch.setattr(agent_graph, "commit_sandbox_changes", lambda sandbox, original: None)
    monkeypatch.setattr(agent_graph, "save_vector_memory", lambda issue, fix: None)
    monkeypatch.setattr(agent_graph, "save_memory", lambda record: None)
    monkeypatch.setattr(agent_graph, "create_fix_pr",
                         lambda url, path, fix: {"success": True, "pr_url": "https://x/pull/1"})
    monkeypatch.setattr(agent_graph, "record_run_start", lambda: "run-1")
    monkeypatch.setattr(agent_graph, "record_bug_detected", lambda **kw: None)
    monkeypatch.setattr(agent_graph, "record_fix_result", lambda **kw: None)
    monkeypatch.setattr(agent_graph, "record_pr_created", lambda: None)
    monkeypatch.setattr(agent_graph, "record_run_summary", lambda **kw: None)
    monkeypatch.setattr(agent_graph, "record_stage_latency", lambda *a: None)

    graph = build_graph()
    final_state = graph.invoke({"repo_url": "https://github.com/org/app"})

    assert len(final_state["issue_results"]) == 2
    assert final_state["issue_results"][0] == {
        "file": "missing.py", "success": False, "retries": 0,
        "pr_url": None, "severity": "high",
    }
    assert final_state["issue_results"][1]["file"] == "app.py"
    assert final_state["issue_results"][1]["success"] is True
