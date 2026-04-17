from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from src.main import analyze_repository
from src.agents.fix_generator import generate_fix
from src.tools.file_tools import read_file
from src.tools.diff_tools import generate_diff
from src.core.logger import get_logger

logger = get_logger("RepoMind.Routes")
router = APIRouter()


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


class DiffRequest(BaseModel):
    old: str
    new: str
    filename: str = "file"


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
            raise HTTPException(
                status_code=404,
                detail=f"File not found or empty: {req.file}"
            )

        new_code = generate_fix(req.file, old_code, req.bug)

        return {"old": old_code, "new": new_code}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fix endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diff")
def diff(req: DiffRequest):
    try:
        return {"diff": generate_diff(req.old, req.new, req.filename)}
    except Exception as e:
        logger.error(f"Diff endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
