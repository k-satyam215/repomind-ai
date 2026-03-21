import shutil
import os
import tempfile


def create_sandbox_copy(repo_path: str):

    sandbox_dir = tempfile.mkdtemp(prefix="repomind_")
    sandbox_repo = os.path.join(sandbox_dir, "repo")

    shutil.copytree(repo_path, sandbox_repo)

    return sandbox_repo


def commit_sandbox_changes(sandbox_repo, original_repo):

    for root, _, files in os.walk(sandbox_repo):

        for f in files:

            sandbox_file = os.path.join(root, f)

            rel = os.path.relpath(sandbox_file, sandbox_repo)

            original_file = os.path.join(original_repo, rel)

            os.makedirs(os.path.dirname(original_file), exist_ok=True)

            shutil.copy2(sandbox_file, original_file)