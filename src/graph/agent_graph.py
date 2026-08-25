import os
import shutil
import time
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.fix_generator import generate_fix
from src.agents.planner_agent import plan_next_step
from src.agents.reflection_agent import reflect_on_failure
from src.core.config import MAX_RETRIES
from src.core.logger import get_logger
from src.integrations.github_pr_agent import create_fix_pr
from src.main import analyze_repository
from src.mcp.client import mcp_call
from src.memory.simple_memory import save_memory
from src.memory.vector_memory import save_vector_memory, search_similar_bug
from src.observability.metrics import (
    record_bug_detected,
    record_fix_result,
    record_pr_created,
    record_run_start,
    record_run_summary,
    record_stage_latency,
    timed_stage,
)
from src.tools.ast_validator import validate_python_syntax
from src.tools.dependency_graph import get_related_files
from src.tools.sandbox_patch import commit_sandbox_changes, create_sandbox_copy

logger = get_logger("RepoMind.Graph")


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    repo_url: str
    repo_data: Dict[str, Any]

    # Multi-issue tracking
    current_issue_index: int       # which issue we are currently fixing
    issue_results: List[dict]      # results for all issues: [{file, success, pr_url, retries}]

    # Per-issue working state
    fix: str
    test_result: Dict[str, Any]
    retry_count: int
    reflection: str
    action: str
    current_file: str
    original_code: str
    sandbox_repo: str
    patch_status: Dict[str, Any]

    # Run tracking
    run_id: str
    run_start_ms: float


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cleanup_sandbox(state: AgentState) -> None:
    sandbox = state.get("sandbox_repo")
    if sandbox and os.path.exists(sandbox):
        shutil.rmtree(sandbox, ignore_errors=True)
        logger.debug(f"Sandbox cleaned up: {sandbox}")


def _current_issue(state: AgentState) -> dict | None:
    issues: List[dict] = state.get("repo_data", {}).get("issues", [])
    idx = state.get("current_issue_index", 0)
    return issues[idx] if idx < len(issues) else None


# ─── Nodes ────────────────────────────────────────────────────────────────────

def analysis_node(state: AgentState) -> dict:
    run_id = record_run_start()
    run_start_ms = time.perf_counter() * 1000

    logger.info(f"[{run_id}] Analyzing repo: {state['repo_url']}")

    with timed_stage("analyze"):
        result = analyze_repository(state["repo_url"])

    # Record each detected bug's metadata
    for issue in result.get("issues", []):
        report = issue.get("report", {})
        record_bug_detected(
            severity=report.get("severity", "medium"),
            bug_type=report.get("bug_type", "other")
        )

    return {
        "repo_data": result,
        "retry_count": 0,
        "current_issue_index": 0,
        "issue_results": [],
        "run_id": run_id,
        "run_start_ms": run_start_ms
    }


def fix_node(state: AgentState) -> dict:
    retry_count = state.get("retry_count", 0)

    if retry_count >= MAX_RETRIES:
        logger.warning(f"Max retries ({MAX_RETRIES}) reached — moving to next issue")
        issue = _current_issue(state)
        severity = issue.get("report", {}).get("severity", "medium") if issue else "medium"
        record_fix_result(success=False, retry_count=retry_count, severity=severity)
        results = list(state.get("issue_results", []))
        results.append({
            "file": issue.get("file", "unknown") if issue else "unknown",
            "success": False,
            "retries": retry_count,
            "pr_url": None,
            "severity": severity,
        })
        next_idx = state.get("current_issue_index", 0) + 1
        return {
            "issue_results": results,
            "current_issue_index": next_idx,
            "retry_count": 0,
            "reflection": "",
            "action": "stop" if next_idx >= len(state.get("repo_data", {}).get("issues", [])) else "next_issue",
        }

    issue = _current_issue(state)
    if issue is None:
        logger.info("All issues processed")
        return {"action": "stop"}

    repo_path: str = state["repo_data"]["repo_path"]
    dep_map: dict = state["repo_data"].get("dependency_map", {})

    main_file: str = issue["file"]
    related_files: List[str] = get_related_files(main_file, dep_map)

    # Build full context: main file + up to 3 related files
    context = ""

    main_res = mcp_call("read_file", {"path": os.path.join(repo_path, main_file)})
    main_code: str = main_res.get("output", "")

    if not main_code:
        logger.error(f"Could not read main file: {main_file}")
        return {"action": "next_issue"}

    context += f"### FILE: {main_file}\n{main_code}\n"

    for rf in related_files[:3]:
        rf_res = mcp_call("read_file", {"path": os.path.join(repo_path, rf)})
        rf_code = rf_res.get("output", "")
        if rf_code:
            context += f"\n### FILE: {rf}\n{rf_code}\n"

    # Augment with similar past fix from vector memory
    similar = search_similar_bug(issue["report"])
    if similar:
        context += f"\n### SIMILAR PAST FIX (for reference)\n{similar}\n"
        logger.debug("Similar bug found in vector memory — context augmented")

    # Append reflection hint from previous failed attempt
    reflection = state.get("reflection", "")
    if reflection:
        context += f"\n### PREVIOUS ATTEMPT FAILED — REASON\n{reflection}\n"

    with timed_stage("fix_generate"):
        fix = generate_fix(main_file, context, issue["report"], repo_path)

    if fix == main_code:
        logger.warning(f"No code change generated for '{main_file}'")
        return {
            "retry_count": retry_count + 1,
            "reflection": "The generated fix did not change the original file.",
            "action": "retry",
        }

    # Validate the fix is valid Python BEFORE applying it
    validation = validate_python_syntax(fix)
    if not validation["valid"]:
        logger.warning(f"Fix failed syntax validation: {validation['error']}")
        return {
            "retry_count": retry_count + 1,
            "reflection": f"Syntax error in generated fix: {validation['error']}",
            "action": "retry"
        }

    logger.info(f"Fix generated and validated for '{main_file}'")
    return {
        "fix": fix,
        "current_file": main_file,
        "original_code": main_code,
        "action": None
    }


def apply_patch_node(state: AgentState) -> dict:
    original_repo: str = state["repo_data"]["repo_path"]

    # Always work in a sandbox — never touch original repo until tests pass
    sandbox_repo = create_sandbox_copy(original_repo)

    with timed_stage("patch_apply"):
        result = mcp_call("apply_patch", {
            "repo_path": sandbox_repo,
            "file": state["current_file"],
            "code": state["fix"]
        })

    if not result.get("success"):
        logger.warning(f"Patch application failed: {result.get('error')}")

    return {
        "sandbox_repo": sandbox_repo,
        "patch_status": result
    }


def test_node(state: AgentState) -> dict:
    if not state.get("patch_status", {}).get("success"):
        return {
            "test_result": {
                "success": False,
                "output": "Patch failed — skipping tests"
            }
        }

    with timed_stage("test_run"):
        result = mcp_call("run_tests", {"repo_path": state["sandbox_repo"]})

    return {"test_result": result}


def reflection_node(state: AgentState) -> dict:
    """
    Evaluate test results.
    On success: commit changes, save memory, create PR, advance to next issue.
    On failure: reflect, plan, increment retry.
    Sandbox cleanup is ALWAYS done here — no leaks.
    """
    patch_ok = state.get("patch_status", {}).get("success", False)
    test_ok = state.get("test_result", {}).get("success", False)
    issue = _current_issue(state)
    retry_count = state.get("retry_count", 0)
    severity = issue.get("report", {}).get("severity", "medium") if issue else "medium"

    try:
        if not patch_ok:
            record_fix_result(success=False, retry_count=retry_count, severity=severity)
            return {
                "retry_count": retry_count + 1,
                "reflection": f"Patch application failed: {state['patch_status'].get('error', 'unknown')}",
                "action": "retry"
            }

        if test_ok:
            logger.info("Fix validated — committing to original repo")

            # Commit sandbox → original
            commit_sandbox_changes(
                state["sandbox_repo"],
                state["repo_data"]["repo_path"]
            )

            # Persist memory
            save_vector_memory(issue, state["fix"])
            save_memory({
                "bug": issue,
                "fix": state["fix"],
                "result": "success"
            })

            # Create PR — non-blocking failure
            pr_url = None
            try:
                pr_result = create_fix_pr(
                    state["repo_data"]["repo_url"],
                    state["repo_data"]["repo_path"],
                    state["fix"]
                )
                if pr_result.get("success"):
                    pr_url = pr_result.get("pr_url")
                    record_pr_created()
            except Exception as pr_err:
                logger.warning(f"PR creation skipped: {pr_err}")

            # Record metrics
            record_fix_result(success=True, retry_count=retry_count, severity=severity)

            # Record issue result
            issue_results = list(state.get("issue_results", []))
            issue_results.append({
                "file": state["current_file"],
                "success": True,
                "retries": retry_count,
                "pr_url": pr_url,
                "severity": severity
            })

            next_idx = state.get("current_issue_index", 0) + 1
            total_issues = len(state["repo_data"].get("issues", []))

            if next_idx >= total_issues:
                return {
                    "issue_results": issue_results,
                    "action": "stop"
                }

            # Advance to next issue
            return {
                "issue_results": issue_results,
                "current_issue_index": next_idx,
                "retry_count": 0,
                "reflection": "",
                "action": "next_issue"
            }

        # Tests failed — reflect and plan retry
        with timed_stage("reflection"):
            reflection = reflect_on_failure(
                issue,
                state["fix"],
                state["test_result"].get("output", "")
            )
        decision = plan_next_step(reflection)

        if decision == "stop":
            record_fix_result(success=False, retry_count=retry_count, severity=severity)
            issue_results = list(state.get("issue_results", []))
            issue_results.append({
                "file": state["current_file"],
                "success": False,
                "retries": retry_count,
                "pr_url": None,
                "severity": severity
            })
            return {
                "issue_results": issue_results,
                "action": "next_issue"
            }

        return {
            "retry_count": retry_count + 1,
            "reflection": reflection,
            "action": decision
        }

    finally:
        # ALWAYS clean up sandbox — even if an exception occurs above
        _cleanup_sandbox(state)


def finalize_node(state: AgentState) -> dict:
    """Record run summary metrics after all issues processed."""
    run_start_ms = state.get("run_start_ms", time.perf_counter() * 1000)
    duration_ms = (time.perf_counter() * 1000) - run_start_ms

    issue_results = state.get("issue_results", [])
    bugs = len(state.get("repo_data", {}).get("issues", []))
    fixes = sum(1 for r in issue_results if r.get("success"))

    record_run_summary(
        run_id=state.get("run_id", "unknown"),
        repo_url=state.get("repo_url", ""),
        bugs=bugs,
        fixes=fixes,
        success=fixes > 0,
        duration_ms=duration_ms
    )

    record_stage_latency("total_pipeline", duration_ms)
    logger.info(
        f"Run complete | bugs={bugs} fixes={fixes} "
        f"success_rate={fixes/bugs*100:.0f}% duration={duration_ms:.0f}ms"
        if bugs > 0 else "Run complete | no bugs found"
    )
    return {}


# ─── Graph ────────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("analysis", analysis_node)
    graph.add_node("fix", fix_node)
    graph.add_node("apply_patch", apply_patch_node)
    graph.add_node("test", test_node)
    graph.add_node("reflect", reflection_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("analysis")

    graph.add_edge("analysis", "fix")
    graph.add_edge("fix", "apply_patch")
    graph.add_edge("apply_patch", "test")
    graph.add_edge("test", "reflect")

    graph.add_conditional_edges(
        "reflect",
        lambda s: s.get("action", "stop"),
        {
            "retry": "fix",
            "next_issue": "fix",   # advance index, reset retry, loop back
            "done": "finalize",
            "stop": "finalize",
            "next": "fix"          # alias for next_issue (planner compatibility)
        }
    )

    graph.add_edge("finalize", END)

    return graph.compile()
