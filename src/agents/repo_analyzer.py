from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.core.config import GROQ_API_KEY
from src.core.logger import get_logger

logger = get_logger("RepoMind.RepoAnalyzer")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

SYSTEM_PROMPT = """You are a senior software architect.
Analyze the given project file structure and infer the architecture.

Focus on:
- Core modules and their responsibilities
- Frameworks and libraries used
- Key entry points
- Overall design patterns

Keep the response concise, structured, and under 300 words."""


def analyze_repo_structure(files: List[str]) -> str:
    if not files:
        return "No source files found — analysis skipped."

    structure = "\n".join(files[:80])

    logger.info(f"Analyzing repo structure ({len(files)} files)")

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Project files:\n\n{structure}")
        ]

        res = llm.invoke(messages)

        content = getattr(res, "content", "").strip()

        if not content:
            logger.warning("LLM returned empty analysis")
            return "Analysis failed: empty response from model."

        return content

    except Exception as e:
        logger.error(f"Repo analysis failed: {e}")
        return f"Analysis error: {str(e)}"
