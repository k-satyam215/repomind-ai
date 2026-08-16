import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src.agents.fix_generator import generate_fix, generate_fix_stream, generate_multi_file_fix
from src.agents.parallel_processor import apply_approved_fixes, process_issues_parallel
from src.core.logger import get_logger
from src.main import analyze_repository
from src.observability.metrics import get_metrics
from src.tools.diff_tools import generate_diff
from src.tools.file_tools import read_file

logger = get_logger("RepoMind.Routes")
router = APIRouter()


# ─── Request models ────────────────────────────────────────────────────────────

class RepoRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("https://github.com/"):
            raise ValueError("Only GitHub HTTPS URLs are supported (https://github.com/...)")
        return v


class FixRequest(BaseModel):
    repo_path: str
    file: str
    bug: dict


class StreamFixRequest(BaseModel):
    repo_path: str
    file: str
    bug: dict


class MultiFileFixRequest(BaseModel):
    repo_path: str
    file: str
    related_files: list[str] = []
    bug: dict


class ApproveFixRequest(BaseModel):
    repo_path: str
    approved_fixes: dict[str, str]  # {filename: fixed_code}


class DiffRequest(BaseModel):
    old: str
    new: str
    filename: str = "file"


class ParallelAnalyzeRequest(BaseModel):
    repo_url: str
    max_concurrent: int = 3

    @field_validator("repo_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("https://github.com/"):
            raise ValueError("Only GitHub HTTPS URLs are supported")
        return v


# ─── Standard endpoints ────────────────────────────────────────────────────────

@router.post("/analyze/stream")
async def analyze_stream(req: RepoRequest):
    """
    SSE endpoint that streams live progress events during repo analysis.
    Frontend receives real-time updates: cloning, parsing, detecting bugs, etc.
    """
    import asyncio

    from src.core.cache import cache_get

    logger.info(f"Stream analyze request: {req.repo_url}")

    def _event(stage: str, message: str, data: dict = None) -> str:
        payload = {"stage": stage, "message": message}
        if data:
            payload.update(data)
        return f"data: {json.dumps(payload)}\n\n"

    async def _generator():
        # Check cache first
        cached = cache_get(req.repo_url)
        if cached:
            yield _event("cache", "⚡ Served from Redis cache — instant result!")
            await asyncio.sleep(0.05)
            yield _event("complete", "✅ Analysis complete!", {"result": cached})
            return

        yield _event("start", f"🔗 Starting analysis for {req.repo_url}")
        await asyncio.sleep(0.05)

        yield _event("clone", "📥 Cloning repository from GitHub...")
        await asyncio.sleep(0.05)

        # Run blocking analysis in thread pool

        progress_stages = [
            ("parse",     "🔍 Parsing repository file structure..."),
            ("deps",      "🕸️  Building dependency graph..."),
            ("analyze",   "🧠 Analyzing architecture with LLM..."),
            ("prioritize","📊 Prioritizing files by importance..."),
            ("detect",    "🐛 Running bug detection on each file..."),
        ]

        result_holder = {}
        error_holder = {}

        def _run():
            try:
                result_holder["result"] = analyze_repository(req.repo_url)
            except Exception as e:
                error_holder["error"] = str(e)

        import threading
        thread = threading.Thread(target=_run)
        thread.start()

        # Stream fake progress while analysis runs in background
        stage_idx = 0
        while thread.is_alive():
            if stage_idx < len(progress_stages):
                stage, msg = progress_stages[stage_idx]
                yield _event(stage, msg)
                stage_idx += 1
            await asyncio.sleep(3)  # send update every 3s

        thread.join()

        if error_holder:
            yield _event("error", f"❌ {error_holder['error']}")
            return

        result = result_holder["result"]
        issues = result.get("issues", [])
        crit = sum(1 for i in issues if i.get("report", {}).get("severity") == "critical")
        high = sum(1 for i in issues if i.get("report", {}).get("severity") == "high")
        med  = sum(1 for i in issues if i.get("report", {}).get("severity") == "medium")

        yield _event(
            "complete",
            f"✅ Done! Found {len(issues)} issue(s) — "
            f"{crit} critical, {high} high, {med} medium",
            {"result": result}
        )

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/analyze")
def analyze(req: RepoRequest):
    logger.info(f"Analyze request: {req.repo_url}")
    try:
        result = analyze_repository(req.repo_url)
        if result.get("repo_path") is None and "Error" in result.get("analysis", ""):
            raise HTTPException(status_code=422, detail=result["analysis"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix")
def fix(req: FixRequest):
    logger.info(f"Fix request: {req.file}")
    try:
        old_code = read_file(f"{req.repo_path}/{req.file}")
        if not old_code:
            raise HTTPException(status_code=404, detail=f"File not found or empty: {req.file}")
        new_code = generate_fix(req.file, old_code, req.bug)
        return {"old": old_code, "new": new_code}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fix endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix/multi")
def fix_multi(req: MultiFileFixRequest):
    """
    Generate fixes across multiple related files in one LLM call.
    Returns per-file diffs for preview before any changes are applied.
    """
    logger.info(f"Multi-file fix request: {req.file}")
    try:
        # Build files context
        files_context: dict[str, str] = {}
        main_code = read_file(f"{req.repo_path}/{req.file}")
        if not main_code:
            raise HTTPException(status_code=404, detail=f"File not found: {req.file}")
        files_context[req.file] = main_code

        for rf in req.related_files[:3]:
            rf_code = read_file(f"{req.repo_path}/{rf}")
            if rf_code:
                files_context[rf] = rf_code

        if len(files_context) > 1:
            fixed_files = generate_multi_file_fix(req.file, files_context, req.bug)
        else:
            fixed_code = generate_fix(req.file, main_code, req.bug)
            fixed_files = {req.file: fixed_code} if fixed_code != main_code else {}

        # Build diffs
        diffs = {}
        for fname, new_code in fixed_files.items():
            orig = files_context.get(fname, "")
            d = generate_diff(orig, new_code, fname)
            if d:
                diffs[fname] = d

        return {
            "fixed_files": fixed_files,
            "diffs": diffs,
            "changed_file_count": len(fixed_files)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-file fix error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix/approve")
def approve_fix(req: ApproveFixRequest):
    """
    Human-in-the-loop: apply user-approved fixes to the repo.
    This endpoint is called ONLY after the user clicks 'Approve & Apply' in the UI.
    """
    logger.info(f"Applying {len(req.approved_fixes)} approved fix(es) to {req.repo_path}")
    try:
        result = apply_approved_fixes(req.repo_path, req.approved_fixes)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Apply failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve fix error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix/stream")
def fix_stream(req: StreamFixRequest):
    """
    Stream fix generation token by token via Server-Sent Events.
    Frontend consumes this with fetch() + ReadableStream for real-time display.
    """
    logger.info(f"Streaming fix request: {req.file}")

    old_code = read_file(f"{req.repo_path}/{req.file}")
    if not old_code:
        raise HTTPException(status_code=404, detail=f"File not found: {req.file}")

    def _sse_generator():
        # Send metadata first
        yield f"data: {json.dumps({'type': 'start', 'file': req.file})}\n\n"

        full_fix = []
        try:
            for chunk in generate_fix_stream(req.file, old_code, req.bug):
                full_fix.append(chunk)
                payload = json.dumps({"type": "token", "content": chunk})
                yield f"data: {payload}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Send final assembled fix + diff
        assembled = "".join(full_fix)
        # Strip markdown fences if present
        if assembled.startswith("```"):
            lines = assembled.splitlines()
            assembled = "\n".join(line for line in lines if not line.startswith("```")).strip()

        diff = generate_diff(old_code, assembled, req.file)
        yield f"data: {json.dumps({'type': 'done', 'fix': assembled, 'diff': diff, 'original': old_code})}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/analyze/parallel")
async def analyze_parallel(req: ParallelAnalyzeRequest):
    """
    Analyze repo + process all issues in parallel (async).
    Returns per-issue fix previews with diffs — no changes applied until user approves.
    """
    logger.info(f"Parallel analyze request: {req.repo_url}")
    try:
        # Step 1: clone + detect (blocking, run in executor)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_repository, req.repo_url)

        issues = result.get("issues", [])
        repo_path = result.get("repo_path")
        dep_map = result.get("dependency_map", {})

        if not issues or not repo_path:
            return {**result, "processed_issues": []}

        # Step 2: process all issues in parallel
        processed = await process_issues_parallel(
            issues, repo_path, dep_map, max_concurrent=req.max_concurrent
        )

        return {
            **result,
            "processed_issues": processed,
            "total_issues": len(issues),
            "issues_with_fixes": sum(1 for p in processed if p.get("success")),
            "total_files_to_change": sum(p.get("changed_file_count", 0) for p in processed)
        }

    except Exception as e:
        logger.error(f"Parallel analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diff")
def diff(req: DiffRequest):
    try:
        return {"diff": generate_diff(req.old, req.new, req.filename)}
    except Exception as e:
        logger.error(f"Diff endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
def metrics():
    """
    Live observability endpoint.
    Returns fix success rates, retry distribution, stage latencies,
    severity breakdown, recent run history, Redis status, LangSmith status.
    """
    try:
        from src.core.cache import cache_ping
        from src.core.config import (
            LANGSMITH_PROJECT,
            LANGSMITH_TRACING_ENABLED,
            REDIS_ENABLED,
        )
        data = get_metrics()
        data["integrations"] = {
            "redis": {
                "enabled": REDIS_ENABLED,
                "connected": cache_ping() if REDIS_ENABLED else False,
            },
            "langsmith": {
                "enabled": LANGSMITH_TRACING_ENABLED,
                "project": LANGSMITH_PROJECT if LANGSMITH_TRACING_ENABLED else None,
                "url": (
                    f"https://smith.langchain.com/projects/{LANGSMITH_PROJECT}"
                    if LANGSMITH_TRACING_ENABLED else None
                ),
            },
        }
        return data
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
