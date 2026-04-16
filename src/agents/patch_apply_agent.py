import os
import shutil
from src.core.logger import get_logger

logger = get_logger("RepoMind.PatchApply")


def apply_patch(repo_path: str, file: str, new_code: str) -> dict:
    """
    Write new_code to the target file atomically.

    Strategy:
    1. Write to a temp file alongside the target
    2. Rename (atomic on POSIX) to replace original
    3. Keep .bak backup in case rollback is needed

    Returns {"success": True} or {"success": False, "error": "..."}
    """
    if not new_code or not new_code.strip():
        return {"success": False, "error": "New code is empty — patch rejected"}

    file_path = os.path.join(repo_path, file)

    if not os.path.exists(file_path):
        logger.error(f"File not found for patch: {file_path}")
        return {"success": False, "error": f"File not found: {file}"}

    backup_path = file_path + ".bak"
    tmp_path = file_path + ".tmp"

    try:
        # Step 1: backup original
        shutil.copy2(file_path, backup_path)

        # Step 2: write new content to temp file
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_code)

        # Step 3: atomic replace
        os.replace(tmp_path, file_path)

        logger.info(f"Patch applied successfully: {file}")
        return {"success": True}

    except Exception as e:
        logger.error(f"Patch failed for '{file}': {e}")

        # Rollback: restore backup if exists
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, file_path)
                logger.info(f"Rolled back to backup for: {file}")
            except Exception as rollback_err:
                logger.error(f"Rollback also failed for '{file}': {rollback_err}")

        # Cleanup temp
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        return {"success": False, "error": str(e)}
