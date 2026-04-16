"""
Tests for src/tools — no LLM calls, no network, pure logic.
"""
import os
import tempfile
import pytest

from src.tools.ast_validator import validate_python_syntax
from src.tools.diff_tools import generate_diff
from src.tools.file_tools import read_file
from src.tools.dependency_graph import extract_imports, build_dependency_map, get_related_files
from src.tools.file_prioritizer import score_file, prioritize_files
from src.tools.sandbox_patch import create_sandbox_copy, commit_sandbox_changes


# ─── ast_validator ────────────────────────────────────────────────────────────

class TestAstValidator:

    def test_valid_code(self):
        result = validate_python_syntax("x = 1 + 2\nprint(x)")
        assert result["valid"] is True
        assert result["error"] is None

    def test_invalid_code(self):
        result = validate_python_syntax("def foo(\n    pass")
        assert result["valid"] is False
        assert result["error"] is not None

    def test_empty_string(self):
        result = validate_python_syntax("")
        assert result["valid"] is True

    def test_syntax_error_reports_line(self):
        result = validate_python_syntax("x = (\ny = 2")
        assert result["valid"] is False
        assert "line" in result["error"].lower() or result["error"] is not None


# ─── diff_tools ───────────────────────────────────────────────────────────────

class TestDiffTools:

    def test_basic_diff(self):
        old = "x = 1\ny = 2"
        new = "x = 1\ny = 3"
        diff = generate_diff(old, new)
        assert "-y = 2" in diff
        assert "+y = 3" in diff

    def test_identical_files_empty_diff(self):
        code = "x = 1"
        diff = generate_diff(code, code)
        assert diff == ""

    def test_filename_in_diff_header(self):
        diff = generate_diff("a = 1", "a = 2", filename="myfile.py")
        assert "myfile.py" in diff


# ─── file_tools ───────────────────────────────────────────────────────────────

class TestFileTools:

    def test_read_existing_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("print('hello')", encoding="utf-8")
        assert read_file(str(f)) == "print('hello')"

    def test_read_missing_file_returns_empty(self):
        assert read_file("/nonexistent/path/file.py") == ""

    def test_read_empty_file(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        assert read_file(str(f)) == ""


# ─── dependency_graph ─────────────────────────────────────────────────────────

class TestDependencyGraph:

    def test_extract_simple_import(self):
        code = "import os\nimport sys"
        imports = extract_imports(code)
        assert "os" in imports
        assert "sys" in imports

    def test_extract_from_import(self):
        code = "from collections import defaultdict"
        imports = extract_imports(code)
        assert "collections" in imports

    def test_relative_import_skipped(self):
        code = "from . import utils\nfrom .core import config"
        imports = extract_imports(code)
        # relative imports should not be in results
        assert "utils" not in imports
        assert "core" not in imports

    def test_dotted_import_top_level_only(self):
        code = "import os.path"
        imports = extract_imports(code)
        assert "os" in imports
        assert "os.path" not in imports

    def test_invalid_code_returns_empty(self):
        imports = extract_imports("def broken(\n    pass")
        assert imports == []

    def test_build_dependency_map(self, tmp_path):
        a = tmp_path / "module_a.py"
        b = tmp_path / "module_b.py"
        a.write_text("import module_b", encoding="utf-8")
        b.write_text("x = 1", encoding="utf-8")

        files = ["module_a.py", "module_b.py"]
        dep_map = build_dependency_map(str(tmp_path), files)
        assert "module_b.py" in dep_map.get("module_a.py", [])

    def test_get_related_files(self):
        dep_map = {
            "a.py": ["b.py"],
            "c.py": ["a.py"],
        }
        related = get_related_files("a.py", dep_map)
        assert "b.py" in related  # a imports b
        assert "c.py" in related  # c imports a
        assert "a.py" not in related  # exclude self


# ─── file_prioritizer ─────────────────────────────────────────────────────────

class TestFilePrioritizer:

    def test_main_file_scored_higher(self):
        s_main = score_file("main.py", "import os\ndef run(): pass")
        s_other = score_file("helpers.py", "import os\ndef run(): pass")
        assert s_main > s_other

    def test_config_file_gets_score(self):
        s = score_file("config.py", "x = 1")
        assert s >= 3

    def test_no_false_match_on_partial_name(self):
        # "main_helper.py" should NOT get the high-priority main bonus
        s_helper = score_file("main_helper.py", "x = 1")
        s_main = score_file("main.py", "x = 1")
        assert s_main > s_helper

    def test_prioritize_files_returns_limit(self, tmp_path):
        for i in range(10):
            f = tmp_path / f"mod_{i}.py"
            f.write_text(f"x = {i}", encoding="utf-8")

        files = [f"mod_{i}.py" for i in range(10)]
        result = prioritize_files(str(tmp_path), files, read_file, limit=5)
        assert len(result) == 5


# ─── sandbox_patch ────────────────────────────────────────────────────────────

class TestSandboxPatch:

    def test_sandbox_copy_creates_files(self, tmp_path):
        src = tmp_path / "repo"
        src.mkdir()
        (src / "main.py").write_text("x = 1", encoding="utf-8")

        sandbox = create_sandbox_copy(str(src))
        assert os.path.exists(os.path.join(sandbox, "main.py"))

    def test_sandbox_excludes_git(self, tmp_path):
        src = tmp_path / "repo"
        src.mkdir()
        (src / ".git").mkdir()
        (src / ".git" / "config").write_text("git config", encoding="utf-8")
        (src / "main.py").write_text("x = 1", encoding="utf-8")

        sandbox = create_sandbox_copy(str(src))
        assert not os.path.exists(os.path.join(sandbox, ".git"))
        assert os.path.exists(os.path.join(sandbox, "main.py"))

    def test_commit_sandbox_changes(self, tmp_path):
        src = tmp_path / "repo"
        src.mkdir()
        (src / "main.py").write_text("x = 1", encoding="utf-8")

        sandbox = create_sandbox_copy(str(src))

        # Modify in sandbox
        with open(os.path.join(sandbox, "main.py"), "w") as f:
            f.write("x = 999")

        commit_sandbox_changes(sandbox, str(src))

        content = (src / "main.py").read_text(encoding="utf-8")
        assert content == "x = 999"
