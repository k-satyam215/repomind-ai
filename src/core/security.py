"""Path-boundary checks for the public API and MCP service."""

from pathlib import Path

from src.core.config import REPO_WORKSPACE_ROOT


def managed_repo_path(repo_path: str) -> Path:
    root = Path(REPO_WORKSPACE_ROOT).resolve()
    candidate = Path(repo_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Repository path is not a RepoMind-managed workspace") from exc
    if not candidate.is_dir():
        raise ValueError("Repository path does not exist")
    return candidate


def managed_file_path(repo_path: str, relative_file: str) -> Path:
    repo = managed_repo_path(repo_path)
    path = Path(relative_file)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("File path must be a relative path inside the repository")
    resolved = (repo / path).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError("File path escapes the repository") from exc
    return resolved


def managed_path(path: str) -> Path:
    candidate = Path(path).resolve()
    root = Path(REPO_WORKSPACE_ROOT).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path is not inside the RepoMind workspace") from exc
    return candidate
