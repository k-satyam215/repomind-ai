from typing import Dict, Any
import os
import shutil

from langgraph.graph import StateGraph, END

from src.main import analyze_repository
from src.agents.fix_generator import generate_fix
from src.agents.test_runner_agent import run_tests
from src.agents.reflection_agent import reflect_on_failure
from src.agents.patch_apply_agent import apply_patch
from src.agents.planner_agent import plan_next_step

from src.memory.simple_memory import save_memory
from src.memory.vector_memory import search_similar_bug, save_vector_memory

from src.tools.file_tools import read_file
from src.tools.sandbox_patch import create_sandbox_copy, commit_sandbox_changes
from src.tools.dependency_graph import get_related_files
from src.tools.ast_validator import validate_python_syntax

from src.integrations.github_pr_agent import create_fix_pr

from src.core.logger import get_logger

logger = get_logger("RepoMind")

MAX_RETRIES = 3


class AgentState(dict):
    repo_url: str
    repo_data: Dict[str, Any]
    fix: str
    test_result: Dict[str, Any]
    retry_count: int
    reflection: str
    action: str
    current_file: str
    code: str
    sandbox_repo: str
    patch_status: Dict[str, Any]


def analysis_node(state):

    logger.info("Starting repository analysis")

    result = analyze_repository(state["repo_url"])

    logger.info("Repository analysis completed")

    return {
        "repo_data": result,
        "retry_count": 0
    }


def fix_node(state):

    logger.info("Entering fix generation stage")

    if state.get("retry_count", 0) >= MAX_RETRIES:
        logger.warning("Max retry limit reached")
        return {"action": "stop"}

    issues = state["repo_data"]["issues"]

    if not issues:
        logger.info("No issues found in repository")
        return {"action": "stop"}

    issue = issues[0]
    repo_path = state["repo_data"]["repo_path"]
    dep_map = state["repo_data"].get("dependency_map", {})

    main_file = issue["file"]

    logger.info(f"Generating fix for file: {main_file}")

    related_files = get_related_files(main_file, dep_map)

    context = ""

    main_code = read_file(os.path.join(repo_path, main_file))
    context += f"\n### FILE: {main_file}\n{main_code}\n"

    for rf in related_files[:3]:
        code = read_file(os.path.join(repo_path, rf))
        context += f"\n### FILE: {rf}\n{code}\n"

    similar = search_similar_bug(issue["report"])
    if similar:
        logger.info("Found similar past bug in vector memory")
        context += f"\n### SIMILAR PAST FIX\n{similar}\n"

    fix = generate_fix(main_file, context, issue["report"])

    validation = validate_python_syntax(fix)

    if not validation["valid"]:
        logger.error(f"Generated fix has syntax error: {validation['error']}")
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "reflection": f"Syntax error in generated fix: {validation['error']}",
            "action": "retry"
        }

    logger.info("Fix generation successful")

    return {
        "fix": fix,
        "current_file": main_file,
        "code": main_code
    }


def apply_patch_node(state):

    logger.info("Creating sandbox for patch application")

    original_repo = state["repo_data"]["repo_path"]
    sandbox_repo = create_sandbox_copy(original_repo)

    result = apply_patch(
        sandbox_repo,
        state["current_file"],
        state["fix"]
    )

    if result["success"]:
        logger.info("Patch applied successfully in sandbox")
    else:
        logger.error("Patch application failed")

    return {
        "sandbox_repo": sandbox_repo,
        "patch_status": result
    }


def test_node(state):

    logger.info("Starting test execution")

    if not state["patch_status"]["success"]:
        logger.warning("Skipping tests due to patch failure")
        return {
            "test_result": {
                "success": False,
                "output": "Patch application failed"
            }
        }

    sandbox_repo = state["sandbox_repo"]

    result = run_tests(sandbox_repo)

    if result["success"]:
        logger.info("All tests passed")
    else:
        logger.warning("Tests failed")

    return {"test_result": result}


def reflection_node(state):

    logger.info("Entering reflection stage")

    sandbox_repo = state["sandbox_repo"]

    if not state["patch_status"]["success"]:
        shutil.rmtree(sandbox_repo, ignore_errors=True)

        logger.warning("Retrying due to patch failure")

        return {
            "retry_count": state["retry_count"] + 1,
            "reflection": f"Patch failed: {state['patch_status']['error']}",
            "action": "retry"
        }

    if state["test_result"]["success"]:

        logger.info("Fix validated successfully. Committing changes.")

        commit_sandbox_changes(
            sandbox_repo,
            state["repo_data"]["repo_path"]
        )

        save_vector_memory(
            state["repo_data"]["issues"][0],
            state["fix"]
        )

        save_memory({
            "bug": state["repo_data"]["issues"][0],
            "fix": state["fix"],
            "result": "success"
        })

        try:
            logger.info("Creating GitHub PR")
            create_fix_pr(
                state["repo_data"]["repo_url"],
                state["repo_data"]["repo_path"],
                state["fix"]
            )
        except Exception as e:
            logger.error(f"PR creation failed: {e}")

        shutil.rmtree(sandbox_repo, ignore_errors=True)

        logger.info("Process completed successfully")

        return {"action": "done"}

    reflection = reflect_on_failure(
        state["repo_data"]["issues"][0],
        state["fix"],
        state["test_result"]["output"]
    )

    decision = plan_next_step(reflection)

    shutil.rmtree(sandbox_repo, ignore_errors=True)

    logger.info("Retrying after reflection")

    return {
        "retry_count": state["retry_count"] + 1,
        "reflection": reflection,
        "action": decision
    }


def build_graph():

    logger.info("Building agent execution graph")

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
        lambda s: s["action"],
        {
            "retry": "fix",
            "done": END,
            "stop": END
        }
    )

    return graph.compile()