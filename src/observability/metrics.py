"""
RepoMind Observability — Metrics Tracker

Tracks fix pipeline performance:
- Total runs, successes, failures
- Retry distribution
- Latency per stage
- Bug severity + type breakdown
- Fix success rate by file type

Thread-safe. Persists to JSON. Zero external dependencies.
"""

import json
import os
import threading
import time
from contextlib import contextmanager
from typing import Optional

from src.core.logger import get_logger

logger = get_logger("RepoMind.Metrics")

METRICS_PATH = "./repomind_memory/metrics.json"
_lock = threading.Lock()


def _load() -> dict:
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return _default_metrics()


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _default_metrics() -> dict:
    return {
        "total_runs": 0,
        "total_bugs_detected": 0,
        "total_fixes_attempted": 0,
        "total_fixes_succeeded": 0,
        "total_fixes_failed": 0,
        "total_prs_created": 0,
        "retry_distribution": {"0": 0, "1": 0, "2": 0, "3": 0},
        "severity_distribution": {"critical": 0, "high": 0, "medium": 0},
        "bug_type_distribution": {},
        "stage_latency_ms": {
            "clone": [],
            "analyze": [],
            "detect": [],
            "fix_generate": [],
            "patch_apply": [],
            "test_run": [],
            "reflection": [],
            "total_pipeline": []
        },
        "fix_success_by_severity": {
            "critical": {"success": 0, "fail": 0},
            "high": {"success": 0, "fail": 0},
            "medium": {"success": 0, "fail": 0}
        },
        "recent_runs": []   # last 20 run summaries
    }


def record_run_start() -> str:
    """Start a new run, return run_id."""
    run_id = f"run_{int(time.time() * 1000)}"
    with _lock:
        data = _load()
        data["total_runs"] += 1
        _save(data)
    logger.debug(f"Run started: {run_id}")
    return run_id


def record_bug_detected(severity: str, bug_type: str) -> None:
    with _lock:
        data = _load()
        data["total_bugs_detected"] += 1
        sev = severity if severity in ("critical", "high", "medium") else "medium"
        data["severity_distribution"][sev] = data["severity_distribution"].get(sev, 0) + 1
        data["bug_type_distribution"][bug_type] = (
            data["bug_type_distribution"].get(bug_type, 0) + 1
        )
        _save(data)


def record_fix_result(success: bool, retry_count: int, severity: str = "medium") -> None:
    with _lock:
        data = _load()
        data["total_fixes_attempted"] += 1
        retry_key = str(min(retry_count, 3))
        data["retry_distribution"][retry_key] = (
            data["retry_distribution"].get(retry_key, 0) + 1
        )
        sev = severity if severity in ("critical", "high", "medium") else "medium"
        if success:
            data["total_fixes_succeeded"] += 1
            data["fix_success_by_severity"][sev]["success"] += 1
        else:
            data["total_fixes_failed"] += 1
            data["fix_success_by_severity"][sev]["fail"] += 1
        _save(data)


def record_pr_created() -> None:
    with _lock:
        data = _load()
        data["total_prs_created"] += 1
        _save(data)


def record_stage_latency(stage: str, latency_ms: float) -> None:
    with _lock:
        data = _load()
        if stage not in data["stage_latency_ms"]:
            data["stage_latency_ms"][stage] = []
        data["stage_latency_ms"][stage].append(round(latency_ms, 1))
        # Keep last 100 samples per stage
        data["stage_latency_ms"][stage] = data["stage_latency_ms"][stage][-100:]
        _save(data)


def record_run_summary(run_id: str, repo_url: str, bugs: int, fixes: int,
                        success: bool, duration_ms: float) -> None:
    with _lock:
        data = _load()
        summary = {
            "run_id": run_id,
            "repo": repo_url.rstrip("/").split("/")[-1],
            "bugs_detected": bugs,
            "fixes_applied": fixes,
            "success": success,
            "duration_ms": round(duration_ms, 0),
            "timestamp": int(time.time())
        }
        data["recent_runs"].append(summary)
        data["recent_runs"] = data["recent_runs"][-20:]  # keep last 20
        _save(data)


def get_metrics() -> dict:
    """Return current metrics snapshot with computed aggregates."""
    with _lock:
        data = _load()

    attempted = data["total_fixes_attempted"]
    succeeded = data["total_fixes_succeeded"]
    fix_rate = round((succeeded / attempted * 100), 1) if attempted > 0 else 0.0

    # Compute avg latency per stage
    avg_latency = {}
    for stage, samples in data["stage_latency_ms"].items():
        if samples:
            avg_latency[stage] = round(sum(samples) / len(samples), 1)
        else:
            avg_latency[stage] = None

    return {
        **data,
        "fix_success_rate_pct": fix_rate,
        "avg_stage_latency_ms": avg_latency
    }


@contextmanager
def timed_stage(stage: str):
    """Context manager to auto-record stage latency."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        record_stage_latency(stage, elapsed_ms)
        logger.debug(f"Stage '{stage}' took {elapsed_ms:.1f}ms")
