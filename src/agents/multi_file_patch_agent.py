import os
from src.core.logger import get_logger

logger = get_logger("RepoMind.MultiFilePatch")


def apply_multi_file_patch(repo_path: str, file_changes: dict[str, str]) -> dict:
    """
    Apply fixes to multiple files atomically.

    Strategy:
    - Backup all files first
    - Write all changes
    - If any write fails: rollback ALL files to backups
    - On success: remove all backups

    Returns {"success": True, "changed_files": [...]} or {"success": False, "error": "..."}
    """
    if not file_changes:
        return {"success": True, "changed_files": []}

    backups: dict[str, str] = {}
    changed = list(file_changes.keys())

    # Phase 1: backup all targets
    for fname in changed:
        fpath = os.path.join(repo_path, fname)
        if not os.path.exists(fpath):
            logger.warning(f"Multi-file patch: file not found '{fname}' — skipping")
            continue
        backup_path = fpath + ".bak"
        try:
            import shutil
            shutil.copy2(fpath, backup_path)
            backups[fname] = backup_path
        except Exception as e:
            logger.error(f"Backup failed for '{fname}': {e}")
            return {"success": False, "error": f"Backup failed for {fname}: {e}"}

    # Phase 2: write all changes
    written = []
    try:
        for fname, new_code in file_changes.items():
            if fname not in backups:
                continue
            fpath = os.path.join(repo_path, fname)
            tmp_path = fpath + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(new_code)
            os.replace(tmp_path, fpath)
            written.append(fname)
            logger.info(f"Multi-file patch: wrote '{fname}'")

        # Phase 3: cleanup backups on success
        for fname, bak in backups.items():
            if os.path.exists(bak):
                os.remove(bak)

        return {"success": True, "changed_files": written}

    except Exception as e:
        logger.error(f"Multi-file patch write failed: {e} — rolling back")

        # Rollback all written files
        for fname in written:
            bak = backups.get(fname)
            if bak and os.path.exists(bak):
                import shutil
                try:
                    shutil.copy2(bak, os.path.join(repo_path, fname))
                    logger.info(f"Rolled back '{fname}'")
                except Exception as rb_err:
                    logger.error(f"Rollback failed for '{fname}': {rb_err}")

        # Cleanup backups
        for bak in backups.values():
            if os.path.exists(bak):
                try:
                    os.remove(bak)
                except Exception:
                    pass

        return {"success": False, "error": str(e)}
