import asyncio
import os
import sys
from src.core.logger import get_logger

logger = get_logger("RepoMind.TestRunner")

DEFAULT_TIMEOUT = 300  # seconds


async def _run_pytest(repo_path: str, timeout: int):

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytest",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("Test execution timed out")
        process.kill()
        await process.communicate()
        return {
            "success": False,
            "output": "Test execution timeout"
        }

    output = (stdout or b"").decode(errors="ignore") + \
             (stderr or b"").decode(errors="ignore")

    success = process.returncode == 0

    if success:
        logger.info("Tests passed successfully")
    else:
        logger.warning("Tests failed")

    return {
        "success": success,
        "output": output
    }


def run_tests(repo_path: str):

    logger.info(f"Running tests in repo: {repo_path}")

    if not os.path.exists(repo_path):
        logger.error("Repo path does not exist")
        return {
            "success": False,
            "output": "Invalid repo path"
        }

    try:
        try:
            loop = asyncio.get_running_loop()
            result = loop.run_until_complete(
                _run_pytest(repo_path, DEFAULT_TIMEOUT)
            )
        except RuntimeError:
            result = asyncio.run(
                _run_pytest(repo_path, DEFAULT_TIMEOUT)
            )

        return result

    except Exception as e:
        logger.error(f"Test execution error: {str(e)}")
        return {
            "success": False,
            "output": str(e)
        }