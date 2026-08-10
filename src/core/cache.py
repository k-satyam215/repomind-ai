"""
RepoMind Redis Cache

Provides get/set/delete for analysis results.
Falls back to no-op if Redis is not configured — app works without it.

Usage:
    from src.core.cache import cache_get, cache_set

    result = cache_get(repo_url)
    if result:
        return result   # cache hit — skip clone + analysis

    result = analyze_repository(repo_url)
    cache_set(repo_url, result)
    return result
"""

import hashlib
import json

from src.core.config import REDIS_CACHE_TTL, REDIS_ENABLED, REDIS_URL
from src.core.logger import get_logger

logger = get_logger("RepoMind.Cache")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    if not REDIS_ENABLED:
        return None

    try:
        import redis

        _client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        _client.ping()
        logger.info(f"Redis connected: {REDIS_URL}")
        return _client

    except Exception as e:
        logger.warning(f"Redis unavailable — caching disabled: {e}")
        return None


def _make_key(repo_url: str) -> str:
    """Stable cache key from repo URL."""
    h = hashlib.sha256(repo_url.strip().lower().encode()).hexdigest()[:16]
    return f"repomind:analysis:{h}"


def cache_get(repo_url: str) -> dict | None:
    """
    Return cached analysis result for repo_url, or None on miss.
    repo_path is stripped from cached result — it's temp dir specific.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        raw = client.get(_make_key(repo_url))
        if raw:
            data = json.loads(raw)
            logger.info(f"Cache HIT for: {repo_url}")
            # repo_path is temp-dir — invalid after restart, strip it
            data["repo_path"] = None
            data["cache_hit"] = True
            return data
        logger.debug(f"Cache MISS for: {repo_url}")
        return None

    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


def cache_set(repo_url: str, result: dict) -> None:
    """
    Cache analysis result for repo_url with TTL.
    repo_path is excluded — it's a temp directory.
    """
    client = _get_client()
    if client is None:
        return

    try:
        # Don't cache repo_path — it's a temp dir
        payload = {k: v for k, v in result.items() if k != "repo_path"}
        client.setex(
            _make_key(repo_url),
            REDIS_CACHE_TTL,
            json.dumps(payload, default=str)
        )
        logger.info(
            f"Cache SET for: {repo_url} (TTL={REDIS_CACHE_TTL}s)"
        )
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


def cache_delete(repo_url: str) -> None:
    """Invalidate cache for a specific repo."""
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(_make_key(repo_url))
        logger.info(f"Cache invalidated for: {repo_url}")
    except Exception as e:
        logger.warning(f"Cache delete error: {e}")


def cache_ping() -> bool:
    """Health check — returns True if Redis is reachable."""
    client = _get_client()
    if client is None:
        return False
    try:
        return client.ping()
    except Exception:
        return False
