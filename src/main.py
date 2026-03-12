import tempfile
import git
import os
import shutil

from src.utils.repo_parser import get_repo_structure
from src.utils.repo_filter import filter_repo_files
from src.agents.repo_analyzer import analyze_repo_structure
from src.agents.bug_detector import detect_bugs
from src.tools.file_tools import read_file


def analyze_repository(repo_url: str):

    temp_dir = tempfile.mkdtemp()

    try:
        git.Repo.clone_from(repo_url, temp_dir)

        all_files = get_repo_structure(temp_dir)
        files = filter_repo_files(all_files)

        if not files:
            return {
                "analysis": "No source files found",
                "issues": [],
                "repo_path": temp_dir
            }

        analysis = analyze_repo_structure(files)

        if not analysis:
            analysis = "Analysis failed"

        issues = []

        for f in files[:15]:
            code = read_file(os.path.join(temp_dir, f))

            if not code:
                continue

            bug = detect_bugs(f, code)

            if bug:
                issues.append({
                    "file": f,
                    "report": bug
                })

        return {
            "analysis": analysis,
            "issues": issues,
            "repo_path": temp_dir
        }

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "analysis": f"Error: {str(e)}",
            "issues": [],
            "repo_path": None
        }