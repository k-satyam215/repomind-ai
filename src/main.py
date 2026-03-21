import tempfile
import git
import os
import shutil

from src.utils.repo_parser import get_repo_structure
from src.utils.repo_filter import filter_repo_files
from src.agents.repo_analyzer import analyze_repo_structure
from src.agents.bug_detector import detect_bugs
from src.tools.file_tools import read_file
from src.tools.dependency_graph import build_dependency_map
from src.tools.file_prioritizer import prioritize_files


MAX_ANALYSIS_FILES = 30


def analyze_repository(repo_url: str):

    temp_dir = tempfile.mkdtemp(prefix="repomind_repo_")

    try:
        git.Repo.clone_from(repo_url, temp_dir)

        # parse repo
        all_files = get_repo_structure(temp_dir)
        files = filter_repo_files(all_files)

        if not files:
            return {
                "analysis": "No source files found",
                "issues": [],
                "repo_path": temp_dir,
                "dependency_map": {},
                "repo_url": repo_url
            }

        # dependency graph
        try:
            dep_map = build_dependency_map(temp_dir, files)
        except:
            dep_map = {}

        # architecture analysis
        try:
            analysis = analyze_repo_structure(files)
            if not analysis:
                analysis = "Analysis failed"
        except:
            analysis = "Architecture analysis failed"

        issues = []

        # smart prioritization
        try:
            priority_files = prioritize_files(
                temp_dir,
                files,
                read_file,
                limit=MAX_ANALYSIS_FILES
            )
        except:
            priority_files = files[:MAX_ANALYSIS_FILES]

        for f in priority_files:

            file_path = os.path.join(temp_dir, f)
            code = read_file(file_path)

            if not code:
                continue

            try:
                bug = detect_bugs(f, code)
            except:
                continue

            if bug:
                issues.append({
                    "file": f,
                    "report": bug
                })

        return {
            "analysis": analysis,
            "issues": issues,
            "repo_path": temp_dir,
            "dependency_map": dep_map,
            "repo_url": repo_url 
        }

    except Exception as e:

        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "analysis": f"Error: {str(e)}",
            "issues": [],
            "repo_path": None,
            "dependency_map": {},
            "repo_url": repo_url
        }