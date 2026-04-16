import os
import subprocess
import sys

from src.core.config import TEST_TIMEOUT
from src.core.logger import get_logger

logger = get_logger("RepoMind.TestRunner")


def run_tests(repo_path: str) -> dict:
    """
    Run pytest in the given repo path using subprocess.

    Uses subprocess.run instead of asyncio to avoid event loop conflicts
    when called from within FastAPI / LangGraph (which already run an event loop).

    Returns {"success": bool, "output": str}
    """
    logger.info(f"Running tests in: {repo_path}")

    if not os.path.exists(repo_path):
        logger.error(f"Repo path does not exist: {repo_path}")
        return {"success": False, "output": "Invalid repo path"}

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-q"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT
        )

        output = (result.stdout or "") + (result.stderr or "")
        success = result.returncode == 0

        if success:
            logger.info("Tests passed")
        else:
            logger.warning(f"Tests failed (exit code {result.returncode})")

        return {"success": success, "output": output}

    except subprocess.TimeoutExpired:
        logger.error(f"Test execution timed out after {TEST_TIMEOUT}s")
        return {"success": False, "output": f"Test timeout after {TEST_TIMEOUT}s"}

    except FileNotFoundError:
        logger.error("pytest not found — is it installed in the environment?")
        return {"success": False, "output": "pytest not found in environment"}

    except Exception as e:
        logger.error(f"Test execution error: {e}")
        return {"success": False, "output": str(e)}
