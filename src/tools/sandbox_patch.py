import filecmp
import os
import shutil
import tempfile

from src.core.config import REPO_WORKSPACE_ROOT
from src.core.logger import get_logger

logger = get_logger("RepoMind.Sandbox")


def create_sandbox_copy(repo_path: str) -> str:
    """
    Create an isolated copy of the repo in a temp directory.
    Excludes .git to avoid corrupting the original git state.
    """
    os.makedirs(REPO_WORKSPACE_ROOT, mode=0o700, exist_ok=True)
    sandbox_dir = tempfile.mkdtemp(prefix="sandbox_", dir=REPO_WORKSPACE_ROOT)
    sandbox_repo = os.path.join(sandbox_dir, "repo")

    def ignore_git(dir, contents):
        return [".git"] if ".git" in contents else []

    shutil.copytree(repo_path, sandbox_repo, ignore=ignore_git)
    logger.info(f"Sandbox created: {sandbox_repo}")
    return sandbox_repo


def commit_sandbox_changes(sandbox_repo: str, original_repo: str) -> list[str]:
    """
    Copy only files that differ from the original repository back to it.
    Test artefacts and temporary files are never promoted.
    """
    changed: list[str] = []
    ignored_names = {".git", "__pycache__", ".pytest_cache"}
    for root, dirs, files in os.walk(sandbox_repo):
        # skip .git if it somehow exists
        dirs[:] = [d for d in dirs if d not in ignored_names]

        for f in files:
            sandbox_file = os.path.join(root, f)
            rel = os.path.relpath(sandbox_file, sandbox_repo)
            original_file = os.path.join(original_repo, rel)

            if f.endswith((".bak", ".tmp")):
                continue
            if os.path.exists(original_file) and filecmp.cmp(sandbox_file, original_file, shallow=False):
                continue

            parent = os.path.dirname(original_file)
            if parent:  # guard against empty dirname for root-level files
                os.makedirs(parent, exist_ok=True)

            shutil.copy2(sandbox_file, original_file)
            changed.append(rel)

    logger.info(f"Committed {len(changed)} sandbox change(s) to: {original_repo}")
    return changed
