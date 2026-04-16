import os
import ast
from typing import List, Callable
from src.core.logger import get_logger

logger = get_logger("RepoMind.FilePrioritizer")

# Use exact basename checks to avoid false matches like "main_helper.py"
HIGH_PRIORITY_NAMES = {"main", "app", "application", "server", "core"}
MEDIUM_PRIORITY_NAMES = {"config", "settings"}
LOW_PRIORITY_NAMES = {"utils", "helpers", "common"}


def score_file(path: str, code: str) -> float:
    score = 0.0

    basename = os.path.splitext(os.path.basename(path))[0].lower()

    if basename in HIGH_PRIORITY_NAMES:
        score += 5
    elif basename in MEDIUM_PRIORITY_NAMES:
        score += 3
    elif basename in LOW_PRIORITY_NAMES:
        score += 2

    try:
        tree = ast.parse(code)
        import_count = 0
        func_count = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_count += 1
            if isinstance(node, ast.FunctionDef):
                func_count += 1

        score += import_count
        score += func_count * 0.2

    except SyntaxError:
        pass  # unparseable files still included, just scored lower
    except Exception as e:
        logger.debug(f"Score error for '{path}': {e}")

    return score


def prioritize_files(
    repo_path: str,
    files: List[str],
    read_file: Callable[[str], str],
    limit: int = 30
) -> List[str]:
    """
    Score and rank files by importance.
    Returns top `limit` files sorted by score descending.
    """
    scored: List[tuple] = []

    for f in files:
        try:
            code = read_file(os.path.join(repo_path, f))
            if not code:
                continue
            s = score_file(f, code)
            scored.append((f, s))
        except Exception as e:
            logger.debug(f"Skipping '{f}' during prioritization: {e}")
            continue

    scored.sort(key=lambda x: x[1], reverse=True)
    return [f for f, _ in scored[:limit]]
