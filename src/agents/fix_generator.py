from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.config import GROQ_API_KEY, MAX_FIX_LINES
from src.core.logger import get_logger

logger = get_logger("RepoMind.FixGenerator")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

SYSTEM_PROMPT = """You are a senior Python engineer.

Your task is to fix a specific bug in the given code.

STRICT RULES:
- Return the COMPLETE fixed file — not just the changed lines.
- Keep ALL original code intact. Only modify the buggy section.
- Do NOT add extra comments, explanations, or docstrings.
- Do NOT wrap output in markdown code blocks.
- Output ONLY raw Python code, starting from the first line of the file."""


def generate_fix(file: str, code: str, bug: dict) -> str:
    """
    Generate a fixed version of the complete file.

    Returns the complete fixed file content as a string.
    Returns the original code unchanged on failure (safe fallback).
    """
    if not code or not code.strip():
        logger.warning(f"Empty code passed to fix_generator for '{file}'")
        return code

    logger.info(f"Generating fix for '{file}' | Bug: {bug.get('bug', 'unknown')}")

    try:
        prompt = (
            f"FILE: {file}\n\n"
            f"BUG REPORT:\n{bug}\n\n"
            f"FULL FILE CODE:\n{code[:8000]}"
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        res = llm.invoke(messages)

        if not res or not res.content:
            logger.warning(f"Empty fix response for '{file}'")
            return code

        fix = res.content.strip()

        # Strip accidental markdown fences
        if fix.startswith("```"):
            lines = fix.splitlines()
            fix = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        if not fix:
            logger.warning(f"Fix became empty after stripping markdown for '{file}'")
            return code

        # Safety: if fix is absurdly large, reject it
        if len(fix.splitlines()) > MAX_FIX_LINES:
            logger.warning(
                f"Fix for '{file}' too large ({len(fix.splitlines())} lines > {MAX_FIX_LINES}) — rejected"
            )
            return code

        logger.info(f"Fix generated successfully for '{file}'")
        return fix

    except Exception as e:
        logger.error(f"Fix generation failed for '{file}': {e}")
        return code  # safe fallback: return original unchanged
