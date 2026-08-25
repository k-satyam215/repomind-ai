import ast
import importlib.metadata
import os
import re
import subprocess
import sys
import tempfile
from typing import Generator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.core.config import GROQ_API_KEY, GROQ_MODEL_STRONG, MAX_FIX_LINES, RUN_RUNTIME_VALIDATION
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

_PY_VERSION = sys.version_info
_PY_VERSION_STR = f"{_PY_VERSION.major}.{_PY_VERSION.minor}"

MAX_SELF_HEAL_RETRIES = 3

# Libraries whose syntax/API changed significantly across versions
_TRACKED_LIBS = [
    "langchain", "langchain-core", "langchain-groq", "langgraph",
    "fastapi", "pydantic", "chromadb", "openai", "anthropic",
    "httpx", "uvicorn", "starlette", "sqlalchemy", "celery",
    "redis", "numpy", "pandas", "scikit-learn", "torch",
    "transformers", "huggingface-hub", "datasets", "requests",
    "aiohttp", "flask", "django", "pytest", "click", "typer", "rich",
]


def _get_installed_library_versions() -> dict[str, str]:
    """Return {lib: version} for all tracked libs installed in current env."""
    versions = {}
    for lib in _TRACKED_LIBS:
        try:
            versions[lib] = importlib.metadata.version(lib)
        except importlib.metadata.PackageNotFoundError:
            pass
    return versions


def _format_lib_versions(versions: dict[str, str]) -> str:
    if not versions:
        return "No tracked libraries detected."
    return "\n".join(f"  {lib}=={ver}" for lib, ver in sorted(versions.items()))


def _detect_min_python(code: str) -> str:
    """Scan code for sys.version_info guards, return minimum required version."""
    matches = re.findall(r"sys\.version_info\s*>=\s*\((\d+),\s*(\d+)\)", code)
    if matches:
        major, minor = max(matches, key=lambda x: (int(x[0]), int(x[1])))
        return f"{major}.{minor}"
    return "3.8"


# Build env context once at import time
_LIB_VERSIONS = _get_installed_library_versions()
_LIB_VERSIONS_STR = _format_lib_versions(_LIB_VERSIONS)

SYSTEM_PROMPT = f"""You are a senior Python engineer.

ENVIRONMENT (fix MUST work in this exact environment):
- Python: {_PY_VERSION_STR}
- Installed libraries:
{_LIB_VERSIONS_STR}

RULES:
- Use the EXACT API syntax for the library versions listed above.
- If the API changed between versions, use the version listed above.
- If fix needs a Python feature not in {_PY_VERSION_STR}, provide a fallback.
- Return the COMPLETE fixed file — not just the changed lines.
- Keep ALL original code intact. Only modify the buggy section.
- Do NOT add comments, explanations, or docstrings.
- Do NOT wrap output in markdown code blocks.
- Output ONLY raw Python code starting from line 1."""

MULTI_FILE_SYSTEM_PROMPT = """You are a senior Python engineer fixing a bug across multiple files.

For EACH file that needs changes, output in EXACT format:
  === FILE: path/to/file.py ===
  <complete fixed file content>
  === END FILE ===

Include ONLY files that actually need changes.
Return COMPLETE content — not just changed lines.
No markdown, no backticks."""

SELF_HEAL_SYSTEM_PROMPT = f"""You are a senior Python engineer.

A previous fix attempt FAILED at runtime. Fix it so it runs without errors.

ENVIRONMENT:
- Python: {_PY_VERSION_STR}
- Installed libraries:
{_LIB_VERSIONS_STR}

RULES:
- Read the runtime error carefully — fix EXACTLY what it says.
- Use correct API for the library versions listed above.
- Return COMPLETE fixed file — raw Python only, no markdown."""


# ── Verification helpers ──────────────────────────────────────────────────────

def _strip_fences(fix: str) -> str:
    if fix.startswith("```"):
        lines = fix.splitlines()
        fix = "\n".join(line for line in lines if not line.startswith("```")).strip()
    return fix


def _verify_syntax(code: str) -> tuple[bool, str]:
    """Check syntax with ast.parse(). Returns (ok, error)."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"


def _run_in_subprocess(code: str, repo_path: str = "") -> tuple[bool, str]:
    """
    Actually execute the fixed file in a subprocess to catch ALL runtime errors:
    - ImportError: wrong module name, removed function in new library version
    - AttributeError: renamed class/method in newer lib version
    - TypeError: wrong function signature in new version
    - Any module-level crash on import

    Returns (success, error_output).
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        env = os.environ.copy()
        if repo_path and os.path.exists(repo_path):
            env["PYTHONPATH"] = repo_path + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            cwd=repo_path if repo_path else None
        )

        if result.returncode != 0:
            error = (result.stderr or result.stdout or "Unknown runtime error").strip()
            return False, error

        return True, ""

    except subprocess.TimeoutExpired:
        return False, "Subprocess timed out after 15s"
    except Exception as e:
        return False, str(e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _self_heal(
    file: str,
    broken_code: str,
    original_bug: dict,
    runtime_error: str,
    repo_path: str = "",
    attempt: int = 1
) -> tuple[str, bool]:
    """
    Codex-style self-healing loop.
    Sends the actual runtime error back to LLM -> LLM fixes -> re-verify.
    Recurses up to MAX_SELF_HEAL_RETRIES times.
    Returns (fixed_code, success).
    """
    logger.info(
        f"Self-heal attempt {attempt}/{MAX_SELF_HEAL_RETRIES} for '{file}'"
    )
    logger.info(f"Runtime error: {runtime_error[:200]}")

    prompt = (
        f"FILE: {file}\n\n"
        f"ORIGINAL BUG REPORT:\n{original_bug}\n\n"
        f"PREVIOUS FIX FAILED WITH THIS RUNTIME ERROR:\n{runtime_error}\n\n"
        f"BROKEN CODE THAT FAILED:\n{broken_code[:6000]}"
    )

    try:
        res = llm.invoke([
            SystemMessage(content=SELF_HEAL_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])

        if not res or not res.content:
            return broken_code, False

        healed = _strip_fences(res.content.strip())

        # Syntax check
        syntax_ok, syntax_err = _verify_syntax(healed)
        if not syntax_ok:
            logger.warning(f"Self-heal {attempt}: syntax error: {syntax_err}")
            return broken_code, False

        # Runtime check
        runtime_ok, new_error = _run_in_subprocess(healed, repo_path)
        if runtime_ok:
            logger.info(f"Self-heal {attempt}: SUCCESS — runtime verified")
            return healed, True

        # Recurse if retries left
        if attempt < MAX_SELF_HEAL_RETRIES:
            return _self_heal(
                file, healed, original_bug, new_error, repo_path, attempt + 1
            )

        logger.warning(
            f"Self-heal exhausted {MAX_SELF_HEAL_RETRIES} attempts for '{file}'"
        )
        return broken_code, False

    except Exception as e:
        logger.error(f"Self-heal error: {e}")
        return broken_code, False


def _build_messages(file: str, code: str, bug: dict, repo_path: str = "") -> list:
    min_ver = _detect_min_python(code)
    prompt = (
        f"FILE: {file}\n"
        f"REPO MIN PYTHON: {min_ver} | RUNTIME PYTHON: {_PY_VERSION_STR}\n\n"
        f"BUG REPORT:\n{bug}\n\n"
        f"FULL FILE CODE:\n{code[:8000]}"
    )
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]


# ── Main fix functions ────────────────────────────────────────────────────────

def generate_fix(file: str, code: str, bug: dict, repo_path: str = "") -> str:
    """
    Codex-style fix generation with full runtime verification + self-heal loop:

    1. Generate fix via LLM (version + library-version aware prompt)
    2. Syntax check — ast.parse()
    3. Runtime execution in subprocess — catches ALL real errors:
       ImportError, AttributeError, TypeError, wrong API usage
    4. If runtime fails -> self-heal loop (up to MAX_SELF_HEAL_RETRIES):
       - Actual runtime error sent back to LLM
       - LLM fixes based on the real error message
       - Re-verify runtime
    5. Only return fix if ALL checks pass. Never return broken code.
    """
    if not code or not code.strip():
        logger.warning(f"Empty code for '{file}'")
        return code

    logger.info(
        f"Generating fix for '{file}' | Bug: {bug.get('bug', 'unknown')[:80]}"
    )

    try:
        res = llm.invoke(_build_messages(file, code, bug, repo_path))

        if not res or not res.content:
            logger.warning(f"Empty LLM response for '{file}'")
            return code

        fix = _strip_fences(res.content.strip())

        if not fix or len(fix.splitlines()) > MAX_FIX_LINES:
            logger.warning(f"Fix for '{file}' empty or too large — rejected")
            return code

        # Step 2: Syntax check
        syntax_ok, syntax_err = _verify_syntax(fix)
        if not syntax_ok:
            logger.warning(f"Syntax error in fix: {syntax_err} — self-heal starting")
            fix, healed = _self_heal(file, fix, bug, syntax_err, repo_path)
            if not healed:
                return code
            return fix

        # Running generated code is opt-in because it is not a security sandbox.
        runtime_ok, runtime_err = (True, "")
        if RUN_RUNTIME_VALIDATION:
            runtime_ok, runtime_err = _run_in_subprocess(fix, repo_path)
        if not runtime_ok:
            logger.warning(
                f"Runtime error in fix: {runtime_err[:100]} — self-heal starting"
            )
            fix, healed = _self_heal(file, fix, bug, runtime_err, repo_path)
            if not healed:
                logger.warning(f"Self-heal failed for '{file}' — returning original")
                return code

        logger.info(f"Fix verified for '{file}' (syntax ✓, runtime ✓)")
        return fix

    except Exception as e:
        logger.error(f"Fix generation failed for '{file}': {e}")
        return code


def generate_fix_stream(file: str, code: str, bug: dict) -> Generator[str, None, None]:
    """
    Stream fix generation token by token via SSE.
    Does NOT do runtime verification (speed > safety for streaming).
    Use generate_fix() when a verified fix is required.
    """
    if not code or not code.strip():
        return

    logger.info(f"Streaming fix for '{file}'")

    try:
        for chunk in llm_streaming.stream(_build_messages(file, code, bug)):
            if chunk.content:
                yield chunk.content
    except Exception as e:
        logger.error(f"Streaming fix failed: {e}")
        yield f"\n# Fix generation error: {e}\n"


def generate_multi_file_fix(
    main_file: str,
    files_context: dict[str, str],
    bug: dict
) -> dict[str, str]:
    """
    Generate fixes across multiple related files atomically.
    Each generated fix is runtime-verified — broken fixes are excluded.
    """
    if not files_context:
        return {}

    logger.info(
        f"Multi-file fix for '{main_file}' across {len(files_context)} files"
    )

    context_parts = [
        f"=== FILE: {fname} ===\n{fcode[:4000]}\n=== END FILE ==="
        for fname, fcode in files_context.items()
    ]

    prompt = (
        f"BUG REPORT:\n{bug}\n\n"
        f"Primary file: {main_file}\n\n"
        f"ALL RELEVANT FILES:\n\n" + "\n\n".join(context_parts)
    )

    try:
        res = llm.invoke([
            SystemMessage(content=MULTI_FILE_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])

        if not res or not res.content:
            return {}

        candidates = _parse_multi_file_response(res.content, files_context)

        # Runtime-verify each candidate fix
        verified = {}
        for fname, fixed_code in candidates.items():
            syntax_ok, syntax_err = _verify_syntax(fixed_code)
            if not syntax_ok:
                logger.warning(
                    f"Multi-file fix: syntax error in '{fname}': {syntax_err}"
                )
                continue

            runtime_ok, runtime_err = _run_in_subprocess(fixed_code)
            if not runtime_ok:
                logger.warning(
                    f"Multi-file fix: runtime error in '{fname}': {runtime_err[:100]}"
                )
                continue

            verified[fname] = fixed_code
            logger.info(
                f"Multi-file fix verified: '{fname}' (syntax ✓, runtime ✓)"
            )

        return verified

    except Exception as e:
        logger.error(f"Multi-file fix failed: {e}")
        return {}


def _parse_multi_file_response(
    response: str, original: dict[str, str]
) -> dict[str, str]:
    results: dict[str, str] = {}
    lines = response.splitlines()
    current_file: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("=== FILE:") and line.endswith("==="):
            if current_file and current_lines:
                fixed = _strip_fences("\n".join(current_lines).strip())
                if fixed and len(fixed.splitlines()) <= MAX_FIX_LINES:
                    results[current_file] = fixed
            current_file = line[len("=== FILE:"):line.rfind("===")].strip()
            current_lines = []
        elif line == "=== END FILE ===" and current_file:
            fixed = _strip_fences("\n".join(current_lines).strip())
            if fixed and len(fixed.splitlines()) <= MAX_FIX_LINES:
                results[current_file] = fixed
            current_file = None
            current_lines = []
        elif current_file:
            current_lines.append(line)

    return {
        fname: code
        for fname, code in results.items()
        if fname in original and code != original[fname]
    }
