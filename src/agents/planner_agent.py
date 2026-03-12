from langchain_groq import ChatGroq
from src.core.config import GROQ_API_KEY

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

PROMPT = """
You are an autonomous AI software engineer.

Based on reflection, decide next action.

Return one word:
retry
stop
"""


def plan_next_step(reflection):

    res = llm.invoke(PROMPT + "\nReflection:\n" + reflection)

    decision = res.content.lower()

    if "retry" in decision:
        return "retry"

    return "stop"