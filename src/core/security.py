"""Path-boundary checks for the public API and MCP service, plus
credential handling for private-repository cloning."""

import re
from pathlib import Path

from src.core.config import REPO_WORKSPACE_ROOT


def build_authenticated_clone_url(repo_url: str, token: str | None) -> str:
    """
    Embed a GitHub token into an HTTPS clone URL so `git clone` can access
    private repositories: https://github.com/x/y -> https://<token>@github.com/x/y

    Returns the original URL unchanged if no token is provided (public repos),
    or if the URL isn't a plain https://github.com/... URL (SSH URLs, other
    hosts) -- token-embedding only makes sense for that one specific shape.
    """
    if not token:
        return repo_url
    if not repo_url.startswith("https://github.com/"):
        return repo_url
    return repo_url.replace("https://github.com/", f"https://{token}@github.com/", 1)


def redact_token(text: str, token: str | None) -> str:
    """
    Strip a token out of arbitrary text (git error messages, subprocess
    output, exception strings) before it is ever logged or returned to a
    caller. Git's own exceptions embed the full command line -- including
    the authenticated clone URL -- so this must run on every code path that
    might surface a git error, not just the happy path.
    """
    if not token:
        return text
    return text.replace(token, "***REDACTED***")


_GIT_CONFIG_TOKEN_URL_RE = re.compile(r"https://[^@/]+@github\.com/")


def strip_token_from_git_config(repo_path: str) -> None:
    """
    Defense in depth: after a successful authenticated clone, the token is
    still sitting in plain text in the clone's .git/config (as the remote
    URL) for as long as that temp directory exists. Rewrite the remote URL
    back to a plain, unauthenticated form immediately after cloning so the
    credential doesn't linger on disk any longer than the clone operation
    itself needs it.
    """
    config_path = Path(repo_path) / ".git" / "config"
    if not config_path.is_file():
        return
    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError:
        return
    cleaned = _GIT_CONFIG_TOKEN_URL_RE.sub("https://github.com/", content)
    if cleaned != content:
        config_path.write_text(cleaned, encoding="utf-8")


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
