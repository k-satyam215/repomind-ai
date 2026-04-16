import tempfile
import shutil
import os

import git

from src.utils.repo_parser import get_repo_structure
from src.utils.repo_filter import filter_repo_files
from src.agents.repo_analyzer import analyze_repo_structure
from src.agents.bug_detector import detect_bugs
from src.tools.file_tools import read_file
from src.tools.dependency_graph import build_dependency_map
from src.tools.file_prioritizer import prioritize_files
from src.core.config import MAX_ANALYSIS_FILES
from src.core.logger import get_logger

logger = get_logger("RepoMind.Main")


def analyze_repository(repo_url: str) -> dict:
    """
    Clone a GitHub repo, analyze its architecture, and detect bugs.

    Returns:
        {
            "analysis": str,
            "issues": list,
            "repo_path": str | None,
            "dependency_map": dict,
            "repo_url": str
        }
    """
    temp_dir = tempfile.mkdtemp(prefix="repomind_repo_")
    logger.info(f"Cloning: {repo_url} → {temp_dir}")

    try:
        git.Repo.clone_from(repo_url, temp_dir)
        logger.info("Clone complete")

        # 1. Parse + filter
        all_files = get_repo_structure(temp_dir)
        files = filter_repo_files(all_files)
        logger.info(f"Found {len(files)} Python source files after filtering")

        if not files:
            return _empty_result(temp_dir, repo_url, "No Python source files found")

        # 2. Dependency graph
        try:
            dep_map = build_dependency_map(temp_dir, files)
        except Exception as e:
            logger.warning(f"Dependency graph failed: {e}")
            dep_map = {}

        # 3. Architecture analysis
        try:
            analysis = analyze_repo_structure(files) or "Analysis failed"
        except Exception as e:
            logger.warning(f"Architecture analysis failed: {e}")
            analysis = f"Architecture analysis failed: {e}"

        # 4. Prioritize files for bug detection
        try:
            priority_files = prioritize_files(
                temp_dir, files, read_file, limit=MAX_ANALYSIS_FILES
            )
        except Exception as e:
            logger.warning(f"File prioritization failed: {e} — using first {MAX_ANALYSIS_FILES}")
            priority_files = files[:MAX_ANALYSIS_FILES]

        # 5. Bug detection
        issues = []
        for f in priority_files:
            code = read_file(os.path.join(temp_dir, f))
            if not code:
                continue
            try:
                bug = detect_bugs(f, code)
                if bug:
                    issues.append({"file": f, "report": bug})
                    logger.info(f"Bug detected in: {f}")
            except Exception as e:
                logger.warning(f"Bug detection failed for '{f}': {e}")
                continue

        logger.info(f"Analysis complete. Issues found: {len(issues)}")

        return {
            "analysis": analysis,
            "issues": issues,
            "repo_path": temp_dir,
            "dependency_map": dep_map,
            "repo_url": repo_url
        }

    except git.exc.GitCommandError as e:
        logger.error(f"Git clone failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return _empty_result(None, repo_url, f"Git clone failed: {e}")

    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return _empty_result(None, repo_url, f"Error: {e}")


def _empty_result(repo_path, repo_url, message) -> dict:
    return {
        "analysis": message,
        "issues": [],
        "repo_path": repo_path,
        "dependency_map": {},
        "repo_url": repo_url
    }
