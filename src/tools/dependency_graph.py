import ast
import os
from collections import defaultdict
from typing import Dict, List
from src.core.logger import get_logger

logger = get_logger("RepoMind.DependencyGraph")


def extract_imports(code: str) -> List[str]:
    """
    Extract top-level module names from all import statements.
    Handles both `import x` and `from x import y` forms.
    Relative imports (from . import x) are skipped — they don't map to filenames directly.
    """
    imports: List[str] = []

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top:
                        imports.append(top)

            elif isinstance(node, ast.ImportFrom):
                # level > 0 means relative import — skip, cannot resolve to filename
                if node.module and (node.level == 0):
                    top = node.module.split(".")[0]
                    if top:
                        imports.append(top)

    except SyntaxError as e:
        logger.debug(f"SyntaxError while parsing imports: {e}")
    except Exception as e:
        logger.debug(f"Unexpected error parsing imports: {e}")

    return imports


def build_dependency_map(repo_path: str, files: List[str]) -> Dict[str, List[str]]:
    """
    Build a map of {file -> [files it imports from this repo]}.
    Uses basename (without extension) to match imports to files.
    """
    dep_map: Dict[str, List[str]] = defaultdict(list)

    # Map: module_name -> relative_file_path
    # If two files share a basename, last one wins (documented limitation)
    file_lookup: Dict[str, str] = {
        os.path.splitext(os.path.basename(f))[0]: f
        for f in files
    }

    for f in files:
        path = os.path.join(repo_path, f)

        try:
            with open(path, "r", encoding="utf-8") as fp:
                code = fp.read()
        except Exception as e:
            logger.warning(f"Could not read '{f}' for dependency analysis: {e}")
            continue

        for imp in extract_imports(code):
            if imp in file_lookup:
                dep_map[f].append(file_lookup[imp])

    return dep_map


def get_related_files(target_file: str, dep_map: Dict[str, List[str]]) -> List[str]:
    """
    Return files that `target_file` imports AND files that import `target_file`.
    """
    related: set = set(dep_map.get(target_file, []))

    for f, deps in dep_map.items():
        if target_file in deps:
            related.add(f)

    # exclude self
    related.discard(target_file)

    return list(related)
