import os
from typing import List


def get_repo_structure(repo_path: str) -> List[str]:
    """
    Walk the repo and return all file paths relative to repo_path.
    Includes ALL file types — filtering happens in repo_filter.
    """
    files: List[str] = []

    for root, _, filenames in os.walk(repo_path):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, repo_path)
            files.append(rel_path)

    return files
