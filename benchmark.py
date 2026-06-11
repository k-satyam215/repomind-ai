"""
RepoMind AI — Reproducible Benchmark Runner
============================================

Runs RepoMind's detect → fix → validate pipeline against real-world Python
repositories and produces a structured report.

Usage:
    python benchmark.py                          # run full benchmark suite
    python benchmark.py --output results.json    # save results to file
    python benchmark.py --repo <url>             # run on single repo

Requirements:
    - GROQ_API_KEY set in .env
    - repomind-ai backend running OR run in-process (default)

Output schema per repo:
    {
        "repo": "owner/name",
        "files_analyzed": int,
        "bugs_detected": int,
        "fixes_attempted": int,
        "fixes_validated": int,       # passed pytest
        "fix_success_rate": float,    # 0.0 - 1.0
        "avg_retries": float,
        "total_duration_s": float,
        "severity_breakdown": {...},
        "bug_types": {...}
    }
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

# Make sure src is importable when run from repo root
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import get_logger
from src.graph.agent_graph import build_graph

logger = get_logger("RepoMind.Benchmark")

# ── Benchmark suite ────────────────────────────────────────────────────────────
# Real-world open-source Python repos with known bugs or deliberate issues.
# Chosen to cover small / medium / large size classes.

BENCHMARK_REPOS = [
    # Small — ~10 files
    {
        "url": "https://github.com/realpython/python-basics-exercises",
        "label": "small",
        "expected_min_bugs": 0
    },
    # Medium — ~40 files
    {
        "url": "https://github.com/pallets/click",
        "label": "medium",
        "expected_min_bugs": 0
    },
    # Large — ~100+ files
    {
        "url": "https://github.com/psf/requests",
        "label": "large",
        "expected_min_bugs": 0
    },
]


def run_single(repo_url: str, graph) -> dict:
    """Run the full RepoMind pipeline on one repo and return a result dict."""
    logger.info(f"Benchmarking: {repo_url}")
    start = time.perf_counter()

    try:
        result = graph.invoke({"repo_url": repo_url})
    except Exception as e:
        logger.error(f"Pipeline failed for {repo_url}: {e}")
        return {
            "repo": repo_url.rstrip("/").split("github.com/")[-1],
            "error": str(e),
            "fix_success_rate": 0.0,
            "total_duration_s": round(time.perf_counter() - start, 2)
        }

    duration = round(time.perf_counter() - start, 2)
    repo_data = result.get("repo_data", {})
    issue_results = result.get("issue_results", [])

    issues = repo_data.get("issues", [])
    bugs_detected = len(issues)
    fixes_attempted = len(issue_results)
    fixes_validated = sum(1 for r in issue_results if r.get("success"))
    fix_rate = round(fixes_validated / fixes_attempted, 3) if fixes_attempted > 0 else 0.0
    avg_retries = (
        round(sum(r.get("retries", 0) for r in issue_results) / fixes_attempted, 2)
        if fixes_attempted > 0 else 0.0
    )

    severity_breakdown = {}
    bug_types = {}
    for issue in issues:
        report = issue.get("report", {})
        sev = report.get("severity", "unknown")
        btype = report.get("bug_type", "unknown")
        severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1
        bug_types[btype] = bug_types.get(btype, 0) + 1

    return {
        "repo": repo_url.rstrip("/").split("github.com/")[-1],
        "repo_url": repo_url,
        "files_analyzed": len(repo_data.get("issues", [])),  # proxied
        "bugs_detected": bugs_detected,
        "fixes_attempted": fixes_attempted,
        "fixes_validated": fixes_validated,
        "fix_success_rate": fix_rate,
        "avg_retries": avg_retries,
        "total_duration_s": duration,
        "severity_breakdown": severity_breakdown,
        "bug_types": bug_types
    }


def run_benchmark(repos: list, output_path: Optional[str] = None) -> list:
    graph = build_graph()
    results = []

    print("\n" + "═" * 60)
    print("  RepoMind AI — Benchmark Suite")
    print("═" * 60)

    for entry in repos:
        url = entry if isinstance(entry, str) else entry["url"]
        label = entry.get("label", "") if isinstance(entry, dict) else ""
        tag = f"[{label}] " if label else ""

        print(f"\n{tag}Running: {url}")
        r = run_single(url, graph)
        results.append(r)

        fix_rate_pct = round(r.get("fix_success_rate", 0) * 100, 1)
        print(f"  ✓ bugs={r.get('bugs_detected', 0)} "
              f"fixes={r.get('fixes_validated', 0)}/{r.get('fixes_attempted', 0)} "
              f"rate={fix_rate_pct}% "
              f"duration={r.get('total_duration_s', 0)}s")

    # Aggregate summary
    total_bugs = sum(r.get("bugs_detected", 0) for r in results)
    total_fixes = sum(r.get("fixes_validated", 0) for r in results)
    total_attempted = sum(r.get("fixes_attempted", 0) for r in results)
    overall_rate = round(total_fixes / total_attempted * 100, 1) if total_attempted > 0 else 0

    print("\n" + "─" * 60)
    print(f"  SUMMARY")
    print(f"  Repos tested  : {len(results)}")
    print(f"  Total bugs    : {total_bugs}")
    print(f"  Fixes success : {total_fixes}/{total_attempted} ({overall_rate}%)")
    print("─" * 60 + "\n")

    if output_path:
        output = {
            "summary": {
                "repos_tested": len(results),
                "total_bugs_detected": total_bugs,
                "total_fixes_validated": total_fixes,
                "total_fixes_attempted": total_attempted,
                "overall_fix_success_rate_pct": overall_rate,
            },
            "results": results
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"  Results saved to: {output_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoMind AI Benchmark Runner")
    parser.add_argument("--repo", type=str, help="Run on a single repo URL")
    parser.add_argument("--output", type=str, default=None,
                        help="Save results to JSON file")
    args = parser.parse_args()

    if args.repo:
        repos = [{"url": args.repo, "label": "custom"}]
    else:
        repos = BENCHMARK_REPOS

    run_benchmark(repos, output_path=args.output)
