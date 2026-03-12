from fastapi import APIRouter
from pydantic import BaseModel

from src.main import analyze_repository
from src.agents.fix_generator import generate_fix
from src.tools.file_tools import read_file
from src.tools.diff_tools import generate_diff

router = APIRouter()


class RepoRequest(BaseModel):
    repo_url: str


class FixRequest(BaseModel):
    repo_path: str
    file: str
    bug: dict


class DiffRequest(BaseModel):
    old: str
    new: str


# ⭐ STABLE ANALYSIS ROUTE
@router.post("/analyze")
def analyze(req: RepoRequest):
    return analyze_repository(req.repo_url)


# ⭐ FIX ROUTE
@router.post("/fix")
def fix(req: FixRequest):
    old_code = read_file(f"{req.repo_path}/{req.file}")
    new_code = generate_fix(req.file, old_code, req.bug)

    return {
        "old": old_code,
        "new": new_code
    }


# ⭐ DIFF ROUTE
@router.post("/diff")
def diff(req: DiffRequest):
    return {
        "diff": generate_diff(req.old, req.new)
    }