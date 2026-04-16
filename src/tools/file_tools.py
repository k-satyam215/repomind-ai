from src.core.logger import get_logger

logger = get_logger("RepoMind.FileTools")


def read_file(path: str) -> str:
    """
    Read a file and return its contents.
    Returns empty string on failure and logs the reason.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return ""
    except PermissionError:
        logger.warning(f"Permission denied: {path}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error reading file '{path}': {e}")
        return ""
