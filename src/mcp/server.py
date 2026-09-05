from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator

from src.agents.patch_apply_agent import apply_patch
from src.agents.test_runner_agent import run_tests
from src.core.logger import get_logger
from src.core.security import managed_file_path, managed_path, managed_repo_path
from src.mcp.registry import TOOLS
from src.tools.file_tools import read_file

logger = get_logger("RepoMind.MCPServer")

app = FastAPI(title="RepoMind MCP Server", version="1.0")


class MCPRequest(BaseModel):
    tool: str
    args: dict

    @validator("tool")
    def tool_must_be_registered(cls, v):
        if v not in TOOLS:
            raise ValueError(f"Unknown tool '{v}'. Available: {list(TOOLS.keys())}")
        return v


@app.post("/tool")
def execute_tool(req: MCPRequest) -> Any:
    """
    Dispatch a tool call. Returns tool result or raises HTTP 400/500.
    Uses proper HTTP status codes instead of returning errors with HTTP 200.
    """
    logger.info(f"Tool call: {req.tool} | args: {list(req.args.keys())}")

    try:
        if req.tool == "read_file":
            path = req.args.get("path")
            if not path:
                raise HTTPException(status_code=400, detail="Missing arg: 'path'")
            return {"output": read_file(str(managed_path(path)))}

        elif req.tool == "apply_patch":
            for key in ("repo_path", "file", "code"):
                if key not in req.args:
                    raise HTTPException(status_code=400, detail=f"Missing arg: '{key}'")
            repo = str(managed_repo_path(req.args["repo_path"]))
            # Resolve once here for a clear boundary error before invoking the tool.
            managed_file_path(repo, req.args["file"])
            return apply_patch(repo, req.args["file"], req.args["code"])

        elif req.tool == "run_tests":
            repo_path = req.args.get("repo_path")
            if not repo_path:
                raise HTTPException(status_code=400, detail="Missing arg: 'repo_path'")
            return run_tests(str(managed_repo_path(repo_path)))

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool '{req.tool}' raised unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
