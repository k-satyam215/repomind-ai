import json
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.config import GROQ_API_KEY
from src.core.logger import get_logger

logger = get_logger("RepoMind.BugDetector")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

SYSTEM_PROMPT = """You are a senior Python debugging engineer.

Detect REALISTIC bugs that may break functionality at runtime.

Report:
- Runtime errors
- Wrong imports
- Deprecated APIs
- Incorrect library usage
- Logic mistakes
- Version compatibility issues

DO NOT report:
- Style issues
- Naming conventions
- Performance optimizations

Respond ONLY with valid JSON. No markdown, no backticks, no explanation.

If a bug is found:
{"bug": "...", "impact": "...", "fix_hint": "..."}

If no bug:
{"bug": "none", "impact": "none", "fix_hint": "none"}"""


def detect_bugs(file: str, code: str) -> Optional[dict]:
    """
    Run LLM bug detection on a single file's code.
    Returns a bug dict or None if no bug found / detection failed.
    """
    if not code or not code.strip():
        return None

    logger.debug(f"Detecting bugs in: {file}")

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"FILE: {file}\n\nCODE:\n{code[:7000]}")
        ]

        res = llm.invoke(messages)
        text = res.content.strip()

        # Extract JSON object robustly
        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == 0:
            logger.warning(f"No JSON found in bug detection response for {file}")
            return None

        data = json.loads(text[start:end])

        if data.get("bug", "none").lower() == "none":
            return None

        return data

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error for '{file}': {e}")
        return None
    except Exception as e:
        logger.error(f"Bug detection failed for '{file}': {e}")
        return None
