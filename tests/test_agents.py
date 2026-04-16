"""
Tests for src/agents — LLM calls are mocked so no API key needed.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.agents.patch_apply_agent import apply_patch
from src.agents.test_runner_agent import run_tests


# ─── patch_apply_agent ────────────────────────────────────────────────────────

class TestPatchApplyAgent:

    def test_successful_patch(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1", encoding="utf-8")

        result = apply_patch(str(tmp_path), "target.py", "x = 999")

        assert result["success"] is True
        assert f.read_text(encoding="utf-8") == "x = 999"

    def test_backup_created(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("original", encoding="utf-8")

        apply_patch(str(tmp_path), "target.py", "new content")

        backup = tmp_path / "target.py.bak"
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == "original"

    def test_file_not_found(self, tmp_path):
        result = apply_patch(str(tmp_path), "missing.py", "x = 1")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_empty_code_rejected(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1", encoding="utf-8")

        result = apply_patch(str(tmp_path), "target.py", "")
        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_whitespace_only_rejected(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1", encoding="utf-8")

        result = apply_patch(str(tmp_path), "target.py", "   \n  ")
        assert result["success"] is False


# ─── test_runner_agent ────────────────────────────────────────────────────────

class TestRunnerAgent:

    def test_invalid_path_returns_failure(self):
        result = run_tests("/nonexistent/path/12345")
        assert result["success"] is False
        assert "invalid" in result["output"].lower()

    def test_repo_with_passing_tests(self, tmp_path):
        # Create a simple repo with one passing test
        test_file = tmp_path / "test_sample.py"
        test_file.write_text("def test_always_pass():\n    assert 1 == 1\n", encoding="utf-8")

        result = run_tests(str(tmp_path))
        assert result["success"] is True
        assert "passed" in result["output"].lower()

    def test_repo_with_failing_tests(self, tmp_path):
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("def test_always_fail():\n    assert 1 == 2\n", encoding="utf-8")

        result = run_tests(str(tmp_path))
        assert result["success"] is False

    def test_no_tests_found(self, tmp_path):
        # Empty repo — pytest exits with code 5 (no tests collected)
        result = run_tests(str(tmp_path))
        # no tests is not a "success" but also not a crash
        assert "output" in result


# ─── fix_generator (mocked LLM) ───────────────────────────────────────────────

class TestFixGenerator:

    @patch("src.agents.fix_generator.llm")
    def test_returns_fixed_code(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "x = 999\nprint(x)"
        mock_llm.invoke.return_value = mock_response

        from src.agents.fix_generator import generate_fix
        result = generate_fix("test.py", "x = 1\nprint(x)", {"bug": "wrong value", "impact": "high", "fix_hint": "change to 999"})

        assert result == "x = 999\nprint(x)"

    @patch("src.agents.fix_generator.llm")
    def test_strips_markdown_fences(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "```python\nx = 999\n```"
        mock_llm.invoke.return_value = mock_response

        from src.agents.fix_generator import generate_fix
        result = generate_fix("test.py", "x = 1", {"bug": "x"})

        assert "```" not in result
        assert "x = 999" in result

    @patch("src.agents.fix_generator.llm")
    def test_empty_llm_response_returns_original(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = ""
        mock_llm.invoke.return_value = mock_response

        from src.agents.fix_generator import generate_fix
        original = "x = 1"
        result = generate_fix("test.py", original, {"bug": "x"})

        assert result == original

    @patch("src.agents.fix_generator.llm")
    def test_oversized_fix_rejected(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "\n".join([f"line_{i} = {i}" for i in range(200)])
        mock_llm.invoke.return_value = mock_response

        from src.agents.fix_generator import generate_fix
        original = "x = 1"
        result = generate_fix("test.py", original, {"bug": "x"})

        # Should return original because fix is too large
        assert result == original


# ─── bug_detector (mocked LLM) ────────────────────────────────────────────────

class TestBugDetector:

    @patch("src.agents.bug_detector.llm")
    def test_detects_bug(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = '{"bug": "wrong import", "impact": "crash", "fix_hint": "use correct module"}'
        mock_llm.invoke.return_value = mock_response

        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "import wrongmodule")

        assert result is not None
        assert result["bug"] == "wrong import"

    @patch("src.agents.bug_detector.llm")
    def test_returns_none_when_no_bug(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = '{"bug": "none", "impact": "none", "fix_hint": "none"}'
        mock_llm.invoke.return_value = mock_response

        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "x = 1")

        assert result is None

    @patch("src.agents.bug_detector.llm")
    def test_handles_malformed_json(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "This is not JSON at all"
        mock_llm.invoke.return_value = mock_response

        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "x = 1")

        assert result is None

    def test_empty_code_returns_none(self):
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "")
        assert result is None
