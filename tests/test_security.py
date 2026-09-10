"""
Tests for src/core/security.py's credential-handling helpers, used to
support cloning PRIVATE repositories without ever leaking the GitHub
token to logs, error messages, or persisted results.

These exist because a naive "embed token in the clone URL" implementation
has a real, easy-to-miss vulnerability: git's own exceptions include the
full command line (the authenticated URL) in their message, so a failed
clone on a private repo would otherwise leak the token straight into the
application logs.
"""
from src.core.security import (
    build_authenticated_clone_url,
    redact_token,
    strip_token_from_git_config,
)


# ─── build_authenticated_clone_url ─────────────────────────────────────────

def test_build_authenticated_clone_url_embeds_token():
    url = build_authenticated_clone_url("https://github.com/owner/repo", "ghp_secret123")
    assert url == "https://ghp_secret123@github.com/owner/repo"


def test_build_authenticated_clone_url_no_token_returns_unchanged():
    url = build_authenticated_clone_url("https://github.com/owner/repo", None)
    assert url == "https://github.com/owner/repo"


def test_build_authenticated_clone_url_empty_token_returns_unchanged():
    url = build_authenticated_clone_url("https://github.com/owner/repo", "")
    assert url == "https://github.com/owner/repo"


def test_build_authenticated_clone_url_ignores_non_github_https_urls():
    # SSH URLs, other git hosts -- token-embedding only applies to the one
    # specific https://github.com/... shape it knows how to rewrite safely.
    url = build_authenticated_clone_url("git@github.com:owner/repo.git", "ghp_secret123")
    assert url == "git@github.com:owner/repo.git"


# ─── redact_token ───────────────────────────────────────────────────────────

def test_redact_token_removes_token_from_error_message():
    token = "ghp_supersecrettoken123"
    error = f"Cmd('git') failed: clone https://{token}@github.com/owner/repo returned 128"
    redacted = redact_token(error, token)
    assert token not in redacted
    assert "***REDACTED***" in redacted


def test_redact_token_no_token_returns_unchanged():
    text = "some ordinary error message"
    assert redact_token(text, None) == text


def test_redact_token_handles_multiple_occurrences():
    token = "ghp_abc"
    text = f"first {token} and again {token}"
    redacted = redact_token(text, token)
    assert token not in redacted
    assert redacted.count("***REDACTED***") == 2


# ─── strip_token_from_git_config ───────────────────────────────────────────

def test_strip_token_from_git_config_removes_embedded_token(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    config = git_dir / "config"
    config.write_text(
        '[remote "origin"]\n'
        "\turl = https://ghp_secret123@github.com/owner/repo\n"
        "\tfetch = +refs/heads/*:refs/remotes/origin/*\n",
        encoding="utf-8",
    )

    strip_token_from_git_config(str(tmp_path))

    content = config.read_text(encoding="utf-8")
    assert "ghp_secret123" not in content
    assert "https://github.com/owner/repo" in content


def test_strip_token_from_git_config_missing_config_does_not_raise(tmp_path):
    # No .git/config at all -- must be a silent no-op, not a crash, since
    # this runs as a best-effort cleanup step after every clone.
    strip_token_from_git_config(str(tmp_path))


def test_strip_token_from_git_config_no_token_present_leaves_file_unchanged(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    config = git_dir / "config"
    original = '[remote "origin"]\n\turl = https://github.com/owner/repo\n'
    config.write_text(original, encoding="utf-8")

    strip_token_from_git_config(str(tmp_path))

    assert config.read_text(encoding="utf-8") == original


# ─── End-to-end: analyze_repository() never leaks the token ───────────────

import git

from src import main as main_module


def test_analyze_repository_redacts_token_on_clone_failure(monkeypatch, tmp_path):
    """
    The core guarantee: if a private-repo clone fails (wrong token, revoked
    token, network error), the token must not appear anywhere in the logged
    error or the value returned to the API caller.

    Note: GitPython itself pre-masks credentials embedded in a command's URL
    (rendering them as `*****`) before building the GitCommandError message,
    so in THIS specific failure path the token is already gone by the time
    our own redact_token() runs on it -- confirmed by the assertion below.
    redact_token() remains as defense-in-depth for any other exception type
    or git version where that automatic masking doesn't apply; what matters
    is the outcome (no leak), not which layer caught it.
    """
    monkeypatch.setattr(main_module, "cache_get", lambda *_: None)
    monkeypatch.setattr(main_module, "cache_set", lambda *_: None)
    monkeypatch.setattr(main_module, "REPO_WORKSPACE_ROOT", str(tmp_path))

    token = "ghp_supersecrettoken123"

    def fake_clone_from(url, _to_path, **_kwargs):
        # Simulate exactly what GitPython actually does: the exception
        # message includes the command line, with credentials pre-masked.
        raise git.exc.GitCommandError(f"git clone {url}", 128, stderr="Authentication failed")

    monkeypatch.setattr(git.Repo, "clone_from", fake_clone_from)

    result = main_module.analyze_repository(
        "https://github.com/owner/private-repo", github_token=token
    )

    assert token not in result["analysis"]
    assert result["repo_path"] is None
    assert "Git clone failed" in result["analysis"]


def test_redact_token_still_catches_tokens_gitpython_does_not_mask():
    """
    Defense-in-depth check for redact_token() in isolation: unlike a real
    GitCommandError (which GitPython pre-masks), an arbitrary exception
    message -- e.g. from a different subprocess call, a requests error, or
    a future code path -- could still contain the raw token verbatim. This
    is the case redact_token() exists for.
    """
    token = "ghp_supersecrettoken123"
    raw_message = f"Connection to https://{token}@github.com/owner/repo timed out"
    redacted = redact_token(raw_message, token)
    assert token not in redacted
    assert "***REDACTED***" in redacted


def test_analyze_repository_never_includes_token_in_result(monkeypatch, tmp_path):
    """On the happy path, the returned/cached result must contain the
    original clean repo_url only -- never the token-embedded clone URL."""
    monkeypatch.setattr(main_module, "cache_get", lambda *_: None)
    monkeypatch.setattr(main_module, "cache_set", lambda *_: None)
    monkeypatch.setattr(main_module, "REPO_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(main_module, "get_repo_structure", lambda _p: [])

    def fake_clone_from(url, to_path, **_kwargs):
        import os as _os
        _os.makedirs(_os.path.join(to_path, ".git"), exist_ok=True)

    monkeypatch.setattr(git.Repo, "clone_from", fake_clone_from)

    token = "ghp_supersecrettoken123"
    result = main_module.analyze_repository(
        "https://github.com/owner/private-repo", github_token=token
    )

    assert result["repo_url"] == "https://github.com/owner/private-repo"
    assert token not in str(result)
