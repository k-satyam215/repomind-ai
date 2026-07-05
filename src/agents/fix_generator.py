from typing import Generator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.core.config import GROQ_API_KEY, GROQ_MODEL_STRONG, MAX_FIX_LINES
from src.core.logger import get_logger

logger = get_logger("RepoMind.FixGenerator")

llm = ChatGroq(
    model=GROQ_MODEL_STRONG,
    api_key=GROQ_API_KEY,
    temperature=0
)

llm_streaming = ChatGroq(
    model=GROQ_MODEL_STRONG,
    api_key=GROQ_API_KEY,
    temperature=0,
    streaming=True
)

SYSTEM_PROMPT = """You are a senior Python engineer.

Your task is to fix a specific bug in the given code.

STRICT RULES:
- Return the COMPLETE fixed file — not just the changed lines.
- Keep ALL original code intact. Only modify the buggy section.
- Do NOT add extra comments, explanations, or docstrings.
- Do NOT wrap output in markdown code blocks.
- Output ONLY raw Python code, starting from the first line of the file."""

MULTI_FILE_SYSTEM_PROMPT = """You are a senior Python engineer fixing a bug that spans multiple files.

Your task is to fix a specific bug across all provided files.

STRICT RULES:
- For EACH file that needs changes, output in this EXACT format:
  === FILE: path/to/file.py ===
  <complete fixed file content>
  === END FILE ===
- Include ONLY files that actually need changes.
- Return the COMPLETE content of each changed file — not just the changed lines.
- Do NOT add extra comments, explanations, or docstrings.
- Do NOT wrap output in markdown code blocks."""


def _build_messages(file: str, code: str, bug: dict) -> list:
    prompt = (
        f"FILE: {file}\n\n"
        f"BUG REPORT:\n{bug}\n\n"
        f"FULL FILE CODE:\n{code[:8000]}"
    )
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]


def _strip_fences(fix: str) -> str:
    if fix.startswith("```"):
        lines = fix.splitlines()
        fix = "\n".join(line for line in lines if not line.startswith("```")).strip()
    return fix


def generate_fix(file: str, code: str, bug: dict) -> str:
    """
    Generate a fixed version of the complete file (blocking).
    Returns the original code unchanged on failure (safe fallback).
    """
    if not code or not code.strip():
        logger.warning(f"Empty code passed to fix_generator for '{file}'")
        return code

    logger.info(f"Generating fix for '{file}' | Bug: {bug.get('bug', 'unknown')}")

    try:
        res = llm.invoke(_build_messages(file, code, bug))

        if not res or not res.content:
            logger.warning(f"Empty fix response for '{file}'")
            return code

        fix = _strip_fences(res.content.strip())

        if not fix:
            return code

        if len(fix.splitlines()) > MAX_FIX_LINES:
            logger.warning(f"Fix for '{file}' too large — rejected")
            return code

        logger.info(f"Fix generated successfully for '{file}'")
        return fix

    except Exception as e:
        logger.error(f"Fix generation failed for '{file}': {e}")
        return code


def generate_fix_stream(file: str, code: str, bug: dict) -> Generator[str, None, None]:
    """
    Stream fix generation token by token.
    Yields raw text chunks as they arrive from the LLM.
    Falls back to empty generator on failure.
    """
    if not code or not code.strip():
        return

    logger.info(f"Streaming fix for '{file}' | Bug: {bug.get('bug', 'unknown')}")

    try:
        for chunk in llm_streaming.stream(_build_messages(file, code, bug)):
            if chunk.content:
                yield chunk.content
    except Exception as e:
        logger.error(f"Streaming fix failed for '{file}': {e}")
        yield f"\n# Fix generation error: {e}\n"


def generate_multi_file_fix(
    main_file: str,
    files_context: dict[str, str],
    bug: dict
) -> dict[str, str]:
    """
    Generate fixes across multiple related files atomically.

    Args:
        main_file: Primary file containing the bug
        files_context: {filename: code} for all relevant files
        bug: Bug report dict

    Returns:
        {filename: fixed_code} — only files that changed
    """
    if not files_context:
        return {}

    logger.info(f"Multi-file fix for '{main_file}' across {len(files_context)} files")

    # Build context with all files
    context_parts = []
    for fname, fcode in files_context.items():
        context_parts.append(f"=== FILE: {fname} ===\n{fcode[:4000]}\n=== END FILE ===")

    prompt = (
        f"BUG REPORT:\n{bug}\n\n"
        f"Primary file with bug: {main_file}\n\n"
        f"ALL RELEVANT FILES:\n\n" + "\n\n".join(context_parts)
    )

    try:
        messages = [
            SystemMessage(content=MULTI_FILE_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        res = llm.invoke(messages)

        if not res or not res.content:
            logger.warning("Empty multi-file fix response")
            return {}

        return _parse_multi_file_response(res.content, files_context)

    except Exception as e:
        logger.error(f"Multi-file fix failed: {e}")
        return {}


def _parse_multi_file_response(response: str, original: dict[str, str]) -> dict[str, str]:
    """Parse the structured multi-file fix response."""
    results = {}
    lines = response.splitlines()
    current_file = None
    current_lines = []

    for line in lines:
        if line.startswith("=== FILE:") and line.endswith("==="):
            if current_file and current_lines:
                fixed = "\n".join(current_lines).strip()
                fixed = _strip_fences(fixed)
                if fixed and len(fixed.splitlines()) <= MAX_FIX_LINES:
                    results[current_file] = fixed
            current_file = line[len("=== FILE:"):line.rfind("===")].strip()
            current_lines = []
        elif line == "=== END FILE ===" and current_file:
            fixed = "\n".join(current_lines).strip()
            fixed = _strip_fences(fixed)
            if fixed and len(fixed.splitlines()) <= MAX_FIX_LINES:
                results[current_file] = fixed
            current_file = None
            current_lines = []
        elif current_file:
            current_lines.append(line)

    # Only return files that actually differ from original
    changed = {}
    for fname, fixed_code in results.items():
        orig = original.get(fname, "")
        if fixed_code != orig and fname in original:
            changed[fname] = fixed_code
            logger.info(f"Multi-file fix: changed '{fname}'")

    return changed
