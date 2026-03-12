import os
from typing import List

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "docs",
    "examples",
    "tutorial",
    "tests",
    "build",
    "dist",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode"
}

VALID_EXTENSIONS = {".py"}

def filter_repo_files(files: List[str]) -> List[str]:

    clean_files = []

    for file_path in files:

        parts = file_path.split(os.sep)

        if any(part in IGNORE_DIRS for part in parts):
            continue

        ext = os.path.splitext(file_path)[1]

        if ext in VALID_EXTENSIONS:
            clean_files.append(file_path)

    return clean_files