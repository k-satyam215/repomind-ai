"""
Tests for src/tools — no LLM calls, no network, pure logic.
"""
import os

import pytest

from src.tools.ast_validator import validate_python_syntax
from src.tools.dependency_graph import build_dependency_map, extract_imports, get_related_files
from src.tools.diff_tools import generate_diff
from src.tools.file_prioritizer import prioritize_files, score_file
from src.tools.file_tools import read_file
from src.tools.sandbox_patch import commit_sandbox_changes, create_sandbox_copy


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

    def test_empty_string_is_valid(self):
        result = validate_python_syntax("")
        assert result["valid"] is True

    def test_syntax_error_reports_line(self):
        result = validate_python_syntax("x = (\ny = 2")
        assert result["valid"] is False
        assert result["error"] is not None

    def test_valid_multiline_function(self):
        code = "def foo(x, y):\n    return x + y\n\nresult = foo(1, 2)"
        result = validate_python_syntax(code)
        assert result["valid"] is True

    def test_valid_class_definition(self):
        code = "class Foo:\n    def __init__(self):\n        self.x = 1"
        result = validate_python_syntax(code)
        assert result["valid"] is True

    def test_result_schema(self):
        result = validate_python_syntax("x = 1")
        assert "valid" in result
        assert "error" in result


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

    def test_added_lines_in_diff(self):
        diff = generate_diff("x = 1", "x = 1\ny = 2")
        assert "+y = 2" in diff

    def test_removed_lines_in_diff(self):
        diff = generate_diff("x = 1\ny = 2", "x = 1")
        assert "-y = 2" in diff


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

    def test_read_multiline_file(self, tmp_path):
        content = "line1\nline2\nline3"
        f = tmp_path / "multi.py"
        f.write_text(content, encoding="utf-8")
        assert read_file(str(f)) == content


# ─── dependency_graph ─────────────────────────────────────────────────────────

class TestDependencyGraph:

    def test_extract_simple_import(self):
        imports = extract_imports("import os\nimport sys")
        assert "os" in imports
        assert "sys" in imports

    def test_extract_from_import(self):
        imports = extract_imports("from collections import defaultdict")
        assert "collections" in imports

    def test_relative_import_skipped(self):
        imports = extract_imports("from . import utils\nfrom .core import config")
        assert "utils" not in imports
        assert "core" not in imports

    def test_dotted_import_top_level_only(self):
        imports = extract_imports("import os.path")
        assert "os" in imports
        assert "os.path" not in imports

    def test_invalid_code_returns_empty(self):
        imports = extract_imports("def broken(\n    pass")
        assert imports == []

    def test_empty_code_returns_empty(self):
        imports = extract_imports("")
        assert imports == []

    def test_build_dependency_map(self, tmp_path):
        a = tmp_path / "module_a.py"
        b = tmp_path / "module_b.py"
        a.write_text("import module_b", encoding="utf-8")
        b.write_text("x = 1", encoding="utf-8")
        dep_map = build_dependency_map(str(tmp_path), ["module_a.py", "module_b.py"])
        assert "module_b.py" in dep_map.get("module_a.py", [])

    def test_get_related_files_both_directions(self):
        dep_map = {
            "a.py": ["b.py"],
            "c.py": ["a.py"],
        }
        related = get_related_files("a.py", dep_map)
        assert "b.py" in related   # a imports b
        assert "c.py" in related   # c imports a
        assert "a.py" not in related  # exclude self

    def test_get_related_files_empty_map(self):
        related = get_related_files("a.py", {})
        assert related == []

    def test_get_related_files_no_deps(self):
        dep_map = {"b.py": ["c.py"]}
        related = get_related_files("a.py", dep_map)
        assert related == []


# ─── file_prioritizer ─────────────────────────────────────────────────────────

class TestFilePrioritizer:

    def test_main_file_scored_higher(self):
        s_main = score_file("main.py", "import os\ndef run(): pass")
        s_other = score_file("helpers.py", "import os\ndef run(): pass")
        assert s_main > s_other

    def test_config_file_gets_score(self):
        assert score_file("config.py", "x = 1") >= 3

    def test_no_false_match_on_partial_name(self):
        s_helper = score_file("main_helper.py", "x = 1")
        s_main = score_file("main.py", "x = 1")
        assert s_main > s_helper

    def test_prioritize_files_returns_limit(self, tmp_path):
        for i in range(10):
            (tmp_path / f"mod_{i}.py").write_text(f"x = {i}", encoding="utf-8")
        files = [f"mod_{i}.py" for i in range(10)]
        result = prioritize_files(str(tmp_path), files, read_file, limit=5)
        assert len(result) == 5

    def test_prioritize_files_fewer_than_limit(self, tmp_path):
        (tmp_path / "only.py").write_text("x = 1", encoding="utf-8")
        result = prioritize_files(str(tmp_path), ["only.py"], read_file, limit=10)
        assert len(result) == 1

    def test_score_increases_with_imports(self):
        s_many = score_file("mod.py", "import os\nimport sys\nimport json\nimport re")
        s_few = score_file("mod.py", "import os")
        assert s_many > s_few

    def test_score_increases_with_functions(self):
        s_funcs = score_file("mod.py", "def a(): pass\ndef b(): pass\ndef c(): pass")
        s_none = score_file("mod.py", "x = 1")
        assert s_funcs > s_none

    def test_unparseable_file_still_scored(self):
        # SyntaxError should not raise — file should still get basename score
        s = score_file("config.py", "def broken(\n    pass")
        assert isinstance(s, float)
        assert s >= 0


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
        with open(os.path.join(sandbox, "main.py"), "w") as f:
            f.write("x = 999")
        commit_sandbox_changes(sandbox, str(src))
        assert (src / "main.py").read_text(encoding="utf-8") == "x = 999"

    def test_sandbox_is_independent_of_original(self, tmp_path):
        src = tmp_path / "repo"
        src.mkdir()
        (src / "main.py").write_text("original", encoding="utf-8")
        sandbox = create_sandbox_copy(str(src))
        with open(os.path.join(sandbox, "main.py"), "w") as f:
            f.write("modified")
        # Original should be untouched
        assert (src / "main.py").read_text(encoding="utf-8") == "original"

    def test_sandbox_copies_nested_files(self, tmp_path):
        src = tmp_path / "repo"
        (src / "subdir").mkdir(parents=True)
        (src / "subdir" / "util.py").write_text("y = 2", encoding="utf-8")
        sandbox = create_sandbox_copy(str(src))
        assert os.path.exists(os.path.join(sandbox, "subdir", "util.py"))
