from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.config import GROQ_API_KEY
from src.core.logger import get_logger

logger = get_logger("RepoMind.Planner")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

SYSTEM_PROMPT = """You are an autonomous AI software engineering agent.

Based on a reflection about a failed fix attempt, decide the next action.

You MUST respond with EXACTLY one of these two words — nothing else:
retry
stop

Use "retry" if there is a clear, different strategy to try.
Use "stop" if the bug is unfixable with the available context or max retries are reached."""


def plan_next_step(reflection: str) -> str:
    """
    Returns 'retry' or 'stop' based on LLM reasoning over the reflection.
    Defaults to 'stop' on any ambiguity or failure — safe default.
    """
    logger.info("Planning next step after reflection")

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Reflection:\n{reflection}")
        ]

        res = llm.invoke(messages)
        decision = res.content.strip().lower()

        # Exact match first — avoids "retry later" triggering retry
        if decision == "retry":
            logger.info("Planner decision: retry")
            return "retry"

        if decision == "stop":
            logger.info("Planner decision: stop")
            return "stop"

        # Fallback: check if the word appears clearly
        if "retry" in decision and "stop" not in decision:
            logger.info("Planner decision (fuzzy): retry")
            return "retry"

        logger.info(f"Planner returned ambiguous response '{decision}' — defaulting to stop")
        return "stop"

    except Exception as e:
        logger.error(f"Planner failed: {e} — defaulting to stop")
        return "stop"
