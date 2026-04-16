from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.config import GROQ_API_KEY
from src.core.logger import get_logger

logger = get_logger("RepoMind.Reflection")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

SYSTEM_PROMPT = """You are an expert debugging engineer reviewing a failed automated fix.

Analyze WHY the fix failed and provide a concise, actionable strategy for the next attempt.

Focus on:
- Root cause of the failure
- What the fix got wrong
- A concrete alternative approach

Keep response under 150 words. Be direct."""


def reflect_on_failure(bug: dict, fix: str, test_output: str) -> str:
    logger.info("Reflecting on failed fix attempt")

    try:
        content = (
            f"BUG:\n{bug}\n\n"
            f"ATTEMPTED FIX:\n{fix[:2000]}\n\n"
            f"TEST OUTPUT:\n{test_output[:2000]}"
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=content)
        ]

        res = llm.invoke(messages)
        reflection = res.content.strip()

        logger.info(f"Reflection: {reflection[:100]}...")
        return reflection

    except Exception as e:
        logger.error(f"Reflection failed: {e}")
        return f"Reflection unavailable due to error: {e}"
