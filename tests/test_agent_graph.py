"""Integration coverage for the LangGraph orchestration routes."""

import src.graph.agent_graph as agent_graph


def _disable_metrics(monkeypatch):
    for name in (
        "record_bug_detected",
        "record_fix_result",
        "record_pr_created",
        "record_run_start",
        "record_run_summary",
        "record_stage_latency",
    ):
        monkeypatch.setattr(agent_graph, name, lambda *args, **kwargs: "test-run")


def test_graph_skips_unreadable_file_and_finalizes(monkeypatch):
    """An unreadable issue must advance and never reach patch application."""
    _disable_metrics(monkeypatch)
    monkeypatch.setattr(
        agent_graph,
        "analyze_repository",
        lambda _url: {
            "repo_path": "C:/nonexistent-repomind-test-repository",
            "dependency_map": {},
            "issues": [{"file": "missing.py", "report": {"severity": "high"}}],
        },
    )

    def fake_mcp(tool, _payload):
        assert tool == "read_file", "unreadable issues must not be patched or tested"
        return {"output": ""}

    monkeypatch.setattr(agent_graph, "mcp_call", fake_mcp)

    result = agent_graph.build_graph().invoke(
        {"repo_url": "https://github.com/example/project"},
        {"recursion_limit": 10},
    )

    assert result["current_issue_index"] == 1
    assert result["issue_results"] == [
        {
            "file": "missing.py",
            "success": False,
            "retries": 0,
            "pr_url": None,
            "severity": "high",
        }
    ]
    assert "patch_status" not in result


def test_fix_router_never_patches_control_actions():
    assert agent_graph._route_after_fix({"action": "retry"}) == "fix"
    assert agent_graph._route_after_fix({"action": "next_issue"}) == "fix"
    assert agent_graph._route_after_fix({"action": "stop"}) == "finalize"
    assert agent_graph._route_after_fix({"action": None}) == "apply_patch"
