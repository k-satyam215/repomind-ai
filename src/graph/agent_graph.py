from typing import Dict, Any
from langgraph.graph import StateGraph, END

from src.main import analyze_repository
from src.agents.fix_generator import generate_fix
from src.agents.test_runner_agent import run_tests
from src.agents.reflection_agent import reflect_on_failure
from src.agents.patch_apply_agent import apply_patch
from src.agents.planner_agent import plan_next_step
from src.memory.simple_memory import save_memory


class AgentState(dict):
    repo_url: str
    repo_data: Dict[str, Any]
    fix: str
    test_result: Dict[str, Any]
    retry_count: int
    reflection: str
    action: str


def analysis_node(state):

    result = analyze_repository(state["repo_url"])

    return {
        "repo_data": result,
        "retry_count": 0
    }


def fix_node(state):

    issues = state["repo_data"]["issues"]

    if not issues:
        return {"action": "stop"}

    issue = issues[0]

    fix = generate_fix(issue["file"], "", issue["report"])

    return {"fix": fix, "current_file": issue["file"]}


def apply_patch_node(state):

    repo_path = state["repo_data"]["repo_path"]

    result = apply_patch(repo_path, state["current_file"], state["fix"])

    return {"patch_status": result}


def test_node(state):

    repo_path = state["repo_data"]["repo_path"]

    result = run_tests(repo_path)

    return {"test_result": result}


def reflection_node(state):

    if state["test_result"]["success"]:
        save_memory({
            "bug": state["repo_data"]["issues"][0],
            "fix": state["fix"],
            "result": "success"
        })
        return {"action": "done"}

    reflection = reflect_on_failure(
        state["repo_data"]["issues"][0],
        state["fix"],
        state["test_result"]["output"]
    )

    decision = plan_next_step(reflection)

    return {
        "retry_count": state["retry_count"] + 1,
        "reflection": reflection,
        "action": decision
    }


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
        lambda s: s["action"],
        {
            "retry": "fix",
            "done": END,
            "stop": END
        }
    )

    return graph.compile()