import json
import sys
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.core.config import GROQ_API_KEY, GROQ_MODEL_STRONG
from src.core.logger import get_logger

logger = get_logger("RepoMind.BugDetector")

llm = (
    ChatGroq(model=GROQ_MODEL_STRONG, api_key=GROQ_API_KEY, temperature=0)
    if GROQ_API_KEY
    else None
)

_PY_VERSION_STR = f"{sys.version_info.major}.{sys.version_info.minor}"

SYSTEM_PROMPT = f"""You are a senior Python debugging engineer.

RUNTIME CONTEXT:
- Python version: {_PY_VERSION_STR}
- Flag bugs that are version-specific (e.g. only break on Python < 3.10)
- Flag deprecated APIs for the CURRENT library versions in use

Detect REALISTIC bugs that may break functionality at runtime.

Report:
- Runtime errors (NameError, AttributeError, TypeError, ImportError)
- Wrong or missing imports
- Deprecated APIs (e.g. removed in newer library versions)
- Incorrect library usage (wrong method signatures, wrong args)
- Logic mistakes that produce wrong results
- Version compatibility issues (note affected Python/library versions)

DO NOT report:
- Style issues or PEP 8 violations
- Naming conventions
- Performance optimizations
- Missing docstrings

Respond ONLY with valid JSON. No markdown, no backticks, no explanation.

If a bug is found:
{{
  "bug": "...",
  "impact": "...",
  "fix_hint": "...",
  "severity": "critical|high|medium",
  "confidence": 0.0-1.0,
  "bug_type": "import_error|runtime_error|logic_error|deprecated_api|type_error|other"
}}

If no bug:
{{"bug": "none", "impact": "none", "fix_hint": "none", "severity": "none", "confidence": 1.0, "bug_type": "none"}}

severity guide:
- critical: causes immediate crash or data corruption
- high: breaks core functionality under normal use
- medium: breaks functionality only in edge cases

confidence guide:
- 1.0: 100% certain this is a real bug
- 0.8: very likely a bug
- 0.6: probable bug, context-dependent
- below 0.5: uncertain — do not report"""


def detect_bugs(file: str, code: str) -> Optional[dict]:
    """
    Run LLM bug detection on a single file's code.

    Returns a bug dict with severity + confidence fields, or None if:
    - no bug found
    - confidence below threshold (0.6)
    - detection failed
    """
    if not code or not code.strip():
        return None

    if llm is None:
        logger.warning("Groq is not configured; bug detection skipped")
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

        # Filter low-confidence detections — reduce false positives
        confidence = float(data.get("confidence", 1.0))
        if confidence < 0.6:
            logger.debug(f"Bug skipped — low confidence ({confidence:.2f}) in: {file}")
            return None

        # Ensure all fields present with defaults
        data.setdefault("severity", "medium")
        data.setdefault("confidence", confidence)
        data.setdefault("bug_type", "other")

        logger.info(
            f"Bug detected in '{file}' | severity={data['severity']} "
            f"confidence={confidence:.2f} type={data['bug_type']}"
        )
        return data

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error for '{file}': {e}")
        return None
    except Exception as e:
        logger.error(f"Bug detection failed for '{file}': {e}")
        return None
