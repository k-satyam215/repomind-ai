import os
import shutil
import tempfile

from src.core.logger import get_logger

logger = get_logger("RepoMind.Sandbox")


def create_sandbox_copy(repo_path: str) -> str:
    """
    Create an isolated copy of the repo in a temp directory.
    Excludes .git to avoid corrupting the original git state.
    """
    sandbox_dir = tempfile.mkdtemp(prefix="repomind_")
    sandbox_repo = os.path.join(sandbox_dir, "repo")

    def ignore_git(dir, contents):
        return [".git"] if ".git" in contents else []

    shutil.copytree(repo_path, sandbox_repo, ignore=ignore_git)
    logger.info(f"Sandbox created: {sandbox_repo}")
    return sandbox_repo


def commit_sandbox_changes(sandbox_repo: str, original_repo: str) -> None:
    """
    Copy all changed files from sandbox back to the original repo.
    Skips .git directory. Creates parent dirs safely.
    """
    for root, dirs, files in os.walk(sandbox_repo):
        # skip .git if it somehow exists
        dirs[:] = [d for d in dirs if d != ".git"]

        for f in files:
            sandbox_file = os.path.join(root, f)
            rel = os.path.relpath(sandbox_file, sandbox_repo)
            original_file = os.path.join(original_repo, rel)

            parent = os.path.dirname(original_file)
            if parent:  # guard against empty dirname for root-level files
                os.makedirs(parent, exist_ok=True)

            shutil.copy2(sandbox_file, original_file)

    logger.info(f"Sandbox changes committed to: {original_repo}")
