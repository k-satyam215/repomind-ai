import asyncio
import os
from typing import Any, Dict, List, Optional

from src.agents.bug_detector import detect_bugs
from src.agents.fix_generator import generate_fix, generate_multi_file_fix
from src.agents.multi_file_patch_agent import apply_multi_file_patch
from src.core.logger import get_logger
from src.tools.dependency_graph import get_related_files
from src.tools.diff_tools import generate_diff
from src.tools.file_tools import read_file

logger = get_logger("RepoMind.ParallelProcessor")


async def _process_single_issue(
    issue: dict,
    repo_path: str,
    dep_map: dict,
) -> dict:
    """
    Process one issue asynchronously:
    - Reads main file + related files
    - Generates multi-file fix
    - Returns result dict with diff previews (does NOT apply patches — that requires user approval)
    """
    file_path = issue["file"]
    report = issue["report"]

    loop = asyncio.get_event_loop()

    # Read main file
    main_code = await loop.run_in_executor(
        None, read_file, os.path.join(repo_path, file_path)
    )
    if not main_code:
        logger.warning(f"Could not read '{file_path}' — skipping")
        return {
            "file": file_path,
            "success": False,
            "error": f"Could not read {file_path}",
            "report": report,
            "diffs": {},
            "fixed_files": {}
        }

    # Collect context: main + related files
    related = get_related_files(file_path, dep_map)
    files_context = {file_path: main_code}

    for rf in related[:3]:
        rf_code = await loop.run_in_executor(
            None, read_file, os.path.join(repo_path, rf)
        )
        if rf_code:
            files_context[rf] = rf_code

    # Generate fix (run in executor so it doesn't block event loop)
    if len(files_context) > 1:
        fixed_files = await loop.run_in_executor(
            None, generate_multi_file_fix, file_path, files_context, report
        )
    else:
        fixed_code = await loop.run_in_executor(
            None, generate_fix, file_path, main_code, report
        )
        fixed_files = {file_path: fixed_code} if fixed_code != main_code else {}

    # Build diffs for preview
    diffs = {}
    for fname, new_code in fixed_files.items():
        original = files_context.get(fname, "")
        diff = await loop.run_in_executor(
            None, generate_diff, original, new_code, fname
        )
        if diff:
            diffs[fname] = diff

    logger.info(
        f"Issue processed: '{file_path}' | "
        f"changed_files={list(fixed_files.keys())} | diffs={len(diffs)}"
    )

    return {
        "file": file_path,
        "success": bool(fixed_files),
        "report": report,
        "fixed_files": fixed_files,
        "diffs": diffs,
        "files_context": files_context,
        "changed_file_count": len(fixed_files)
    }


async def process_issues_parallel(
    issues: List[dict],
    repo_path: str,
    dep_map: dict,
    max_concurrent: int = 3
) -> List[dict]:
    """
    Process all issues in parallel with a concurrency limit.

    Uses asyncio.Semaphore to cap concurrent LLM calls at max_concurrent
    (avoids hitting Groq rate limits).
    """
    sem = asyncio.Semaphore(max_concurrent)

    async def _bounded(issue):
        async with sem:
            return await _process_single_issue(issue, repo_path, dep_map)

    tasks = [_bounded(issue) for issue in issues]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Unwrap exceptions into error dicts
    cleaned = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error(f"Issue {i} raised exception: {r}")
            cleaned.append({
                "file": issues[i].get("file", "unknown"),
                "success": False,
                "error": str(r),
                "report": issues[i].get("report", {}),
                "diffs": {},
                "fixed_files": {}
            })
        else:
            cleaned.append(r)

    return cleaned


def apply_approved_fixes(repo_path: str, approved_fixes: dict[str, str]) -> dict:
    """
    Apply user-approved fixes to the actual repo.
    Called ONLY after user clicks 'Approve & Apply' in the UI.

    Args:
        repo_path: path to cloned repo
        approved_fixes: {filename: fixed_code} approved by user

    Returns:
        {"success": True, "applied": [...]} or {"success": False, "error": "..."}
    """
    if not approved_fixes:
        return {"success": True, "applied": []}

    logger.info(f"Applying {len(approved_fixes)} approved fix(es)")
    result = apply_multi_file_patch(repo_path, approved_fixes)

    # Normalize key: apply_multi_file_patch returns "changed_files", routes expect "applied"
    if result.get("success"):
        return {
            "success": True,
            "applied": result.get("changed_files", list(approved_fixes.keys()))
        }
    return result
