import requests

from src.core.config import MCP_TIMEOUT, MCP_URL
from src.core.logger import get_logger

logger = get_logger("RepoMind.MCPClient")


def mcp_call(tool: str, args: dict) -> dict:
    """
    Call a tool on the MCP server.

    Returns the JSON response dict, or {"error": "..."} on failure.
    Always has a timeout to prevent indefinite hanging.
    """
    logger.debug(f"MCP call → tool='{tool}' args_keys={list(args.keys())}")

    try:
        res = requests.post(
            MCP_URL,
            json={"tool": tool, "args": args},
            timeout=MCP_TIMEOUT
        )

        # Treat non-2xx as errors rather than silently returning wrong data
        res.raise_for_status()

        data = res.json()

        # Server may return {"error": ...} with HTTP 200 — surface it clearly
        if "error" in data:
            logger.warning(f"MCP server returned error for tool '{tool}': {data['error']}")

        return data

    except requests.Timeout:
        logger.error(f"MCP call timed out after {MCP_TIMEOUT}s for tool '{tool}'")
        return {"error": f"Timeout after {MCP_TIMEOUT}s"}

    except requests.HTTPError as e:
        logger.error(f"MCP HTTP error for tool '{tool}': {e}")
        return {"error": str(e)}

    except requests.ConnectionError:
        logger.error(f"MCP server unreachable at {MCP_URL}")
        return {"error": "MCP server unreachable"}

    except Exception as e:
        logger.error(f"MCP call failed for tool '{tool}': {e}")
        return {"error": str(e)}
