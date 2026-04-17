import os
import shutil
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
from src.tools.ast_validator import validate_python_syntax
from src.tools.dependency_graph import get_related_files
from src.tools.sandbox_patch import commit_sandbox_changes, create_sandbox_copy

logger = get_logger("RepoMind.Graph")


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    repo_url: str
    repo_data: Dict[str, Any]
    fix: str
    test_result: Dict[str, Any]
    retry_count: int
    reflection: str
    action: str
    current_file: str
    original_code: str
    sandbox_repo: str
    patch_status: Dict[str, Any]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cleanup_sandbox(state: AgentState) -> None:
    sandbox = state.get("sandbox_repo")
    if sandbox and os.path.exists(sandbox):
        shutil.rmtree(sandbox, ignore_errors=True)
        logger.debug(f"Sandbox cleaned up: {sandbox}")


# ─── Nodes ────────────────────────────────────────────────────────────────────

def analysis_node(state: AgentState) -> dict:
    logger.info(f"Analyzing repo: {state['repo_url']}")
    result = analyze_repository(state["repo_url"])
    return {
        "repo_data": result,
        "retry_count": 0
    }


def fix_node(state: AgentState) -> dict:
    retry_count = state.get("retry_count", 0)

    if retry_count >= MAX_RETRIES:
        logger.warning(f"Max retries ({MAX_RETRIES}) reached — stopping")
        return {"action": "stop"}

    issues: List[dict] = state["repo_data"].get("issues", [])
    if not issues:
        logger.info("No issues found — nothing to fix")
        return {"action": "stop"}

    issue = issues[0]
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
        return {"action": "stop"}

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

    fix = generate_fix(main_file, context, issue["report"])

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

    result = mcp_call("run_tests", {"repo_path": state["sandbox_repo"]})
    return {"test_result": result}


def reflection_node(state: AgentState) -> dict:
    """
    Evaluate test results.
    On success: commit changes, save memory, create PR, clean up sandbox.
    On failure: reflect, plan, clean up sandbox, increment retry.
    Sandbox cleanup is ALWAYS done here — no leaks.
    """
    patch_ok = state.get("patch_status", {}).get("success", False)
    test_ok = state.get("test_result", {}).get("success", False)

    try:
        if not patch_ok:
            return {
                "retry_count": state.get("retry_count", 0) + 1,
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
            save_vector_memory(state["repo_data"]["issues"][0], state["fix"])
            save_memory({
                "bug": state["repo_data"]["issues"][0],
                "fix": state["fix"],
                "result": "success"
            })

            # Create PR — non-blocking failure
            try:
                create_fix_pr(
                    state["repo_data"]["repo_url"],
                    state["repo_data"]["repo_path"],
                    state["fix"]
                )
            except Exception as pr_err:
                logger.warning(f"PR creation skipped: {pr_err}")

            return {"action": "done"}

        # Tests failed — reflect and plan retry
        reflection = reflect_on_failure(
            state["repo_data"]["issues"][0],
            state["fix"],
            state["test_result"].get("output", "")
        )
        decision = plan_next_step(reflection)

        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "reflection": reflection,
            "action": decision
        }

    finally:
        # ALWAYS clean up sandbox — even if an exception occurs above
        _cleanup_sandbox(state)


# ─── Graph ────────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("analysis", analysis_node)
    graph.add_node("fix", fix_node)
    graph.add_node("apply_patch", apply_patch_node)
    graph.add_node("test", test_node)
    graph.add_node("reflect", reflection_node)

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
            "done": END,
            "stop": END
        }
    )

    return graph.compile()
