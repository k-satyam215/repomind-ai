import os
import tempfile

from src.core.logger import get_logger

logger = get_logger("RepoMind.PatchApply")


def apply_patch(repo_path: str, file: str, new_code: str) -> dict:
    """
    Write new_code to the target file atomically.

    Writes to a temp file alongside the target and atomically replaces it.
    No backup artifact is left in the repository.

    Returns {"success": True} or {"success": False, "error": "..."}
    """
    if not new_code or not new_code.strip():
        return {"success": False, "error": "New code is empty — patch rejected"}

    # The public API and MCP server validate the repository boundary before
    # calling this low-level helper. Keep the helper reusable in local tooling.
    file_path = os.path.join(repo_path, file)

    if not os.path.exists(file_path):
        logger.error(f"File not found for patch: {file_path}")
        return {"success": False, "error": f"File not found: {file}"}

    tmp_path = ""

    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".repomind-", dir=os.path.dirname(file_path), text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_code)
            f.flush()
            os.fsync(f.fileno())

        # Step 3: atomic replace
        os.replace(tmp_path, file_path)

        logger.info(f"Patch applied successfully: {file}")
        return {"success": True}

    except Exception as e:
        logger.error(f"Patch failed for '{file}': {e}")

        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

        return {"success": False, "error": str(e)}
