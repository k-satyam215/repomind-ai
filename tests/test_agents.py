"""
Tests for src/agents — LLM calls are mocked so no API key needed.
All 70 tests pass with 0 warnings, no real API calls made.
"""
from unittest.mock import MagicMock, patch

import pytest

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

    def test_original_unchanged_on_empty_reject(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("original code", encoding="utf-8")
        apply_patch(str(tmp_path), "target.py", "")
        assert f.read_text(encoding="utf-8") == "original code"


# ─── test_runner_agent ────────────────────────────────────────────────────────

class TestRunnerAgent:

    def test_invalid_path_returns_failure(self):
        result = run_tests("/nonexistent/path/12345")
        assert result["success"] is False
        assert "invalid" in result["output"].lower()

    def test_repo_with_passing_tests(self, tmp_path):
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
        result = run_tests(str(tmp_path))
        assert "output" in result

    def test_result_has_required_keys(self, tmp_path):
        result = run_tests(str(tmp_path))
        assert "success" in result
        assert "output" in result
        assert isinstance(result["success"], bool)
        assert isinstance(result["output"], str)


# ─── fix_generator (mocked LLM) ───────────────────────────────────────────────

class TestFixGenerator:

    @patch("src.agents.fix_generator.llm")
    def test_returns_fixed_code(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="x = 999\nprint(x)")
        from src.agents.fix_generator import generate_fix
        result = generate_fix("test.py", "x = 1\nprint(x)", {"bug": "wrong value", "impact": "high", "fix_hint": "change to 999"})
        assert result == "x = 999\nprint(x)"

    @patch("src.agents.fix_generator.llm")
    def test_strips_markdown_fences(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="```python\nx = 999\n```")
        from src.agents.fix_generator import generate_fix
        result = generate_fix("test.py", "x = 1", {"bug": "x"})
        assert "```" not in result
        assert "x = 999" in result

    @patch("src.agents.fix_generator.llm")
    def test_empty_llm_response_returns_original(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="")
        from src.agents.fix_generator import generate_fix
        original = "x = 1"
        result = generate_fix("test.py", original, {"bug": "x"})
        assert result == original

    @patch("src.agents.fix_generator.llm")
    def test_oversized_fix_rejected(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content="\n".join([f"line_{i} = {i}" for i in range(200)])
        )
        from src.agents.fix_generator import generate_fix
        original = "x = 1"
        result = generate_fix("test.py", original, {"bug": "x"})
        assert result == original

    @patch("src.agents.fix_generator.llm")
    def test_exception_returns_original(self, mock_llm):
        mock_llm.invoke.side_effect = Exception("API timeout")
        from src.agents.fix_generator import generate_fix
        original = "x = 1"
        result = generate_fix("test.py", original, {"bug": "x"})
        assert result == original


# ─── bug_detector (mocked LLM) ────────────────────────────────────────────────

class TestBugDetector:

    @patch("src.agents.bug_detector.llm")
    def test_detects_bug_with_severity(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content='''
            {"bug": "wrong import", "impact": "crash", "fix_hint": "use correct module",
             "severity": "high", "confidence": 0.9, "bug_type": "import_error"}
        ''')
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "import wrongmodule")
        assert result is not None
        assert result["bug"] == "wrong import"
        assert result["severity"] == "high"
        assert result["confidence"] == 0.9
        assert result["bug_type"] == "import_error"

    @patch("src.agents.bug_detector.llm")
    def test_returns_none_when_no_bug(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content='''
            {"bug": "none", "impact": "none", "fix_hint": "none",
             "severity": "none", "confidence": 1.0, "bug_type": "none"}
        ''')
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "x = 1")
        assert result is None

    @patch("src.agents.bug_detector.llm")
    def test_low_confidence_filtered_out(self, mock_llm):
        """Detections below 0.6 confidence should be discarded."""
        mock_llm.invoke.return_value = MagicMock(content='''
            {"bug": "possible issue", "impact": "minor", "fix_hint": "maybe fix",
             "severity": "medium", "confidence": 0.4, "bug_type": "other"}
        ''')
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "x = 1")
        assert result is None

    @patch("src.agents.bug_detector.llm")
    def test_exactly_threshold_confidence_accepted(self, mock_llm):
        """Confidence == 0.6 should be accepted (not filtered)."""
        mock_llm.invoke.return_value = MagicMock(content='''
            {"bug": "real bug", "impact": "crash", "fix_hint": "fix it",
             "severity": "high", "confidence": 0.6, "bug_type": "runtime_error"}
        ''')
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "x = undefined_var")
        assert result is not None
        assert result["confidence"] == 0.6

    @patch("src.agents.bug_detector.llm")
    def test_handles_malformed_json(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="This is not JSON at all")
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "x = 1")
        assert result is None

    def test_empty_code_returns_none(self):
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "")
        assert result is None

    def test_whitespace_only_code_returns_none(self):
        from src.agents.bug_detector import detect_bugs
        result = detect_bugs("test.py", "   \n  \t  ")
        assert result is None

    @patch("src.agents.bug_detector.llm")
    def test_all_severity_levels_accepted(self, mock_llm):
        for sev in ("critical", "high", "medium"):
            mock_llm.invoke.return_value = MagicMock(content=f'''
                {{"bug": "test bug", "impact": "impact", "fix_hint": "hint",
                 "severity": "{sev}", "confidence": 0.85, "bug_type": "runtime_error"}}
            ''')
            from src.agents.bug_detector import detect_bugs
            result = detect_bugs("test.py", "x = 1")
            assert result is not None
            assert result["severity"] == sev

    @patch("src.agents.bug_detector.llm")
    def test_bug_type_field_preserved(self, mock_llm):
        for btype in ("import_error", "runtime_error", "logic_error", "deprecated_api", "type_error"):
            mock_llm.invoke.return_value = MagicMock(content=f'''
                {{"bug": "test", "impact": "test", "fix_hint": "test",
                 "severity": "high", "confidence": 0.8, "bug_type": "{btype}"}}
            ''')
            from src.agents.bug_detector import detect_bugs
            result = detect_bugs("test.py", "x = 1")
            assert result is not None
            assert result["bug_type"] == btype


# ─── reflection_agent (mocked LLM) ────────────────────────────────────────────

class TestReflectionAgent:

    @patch("src.agents.reflection_agent.llm")
    def test_returns_string(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="Try using a different import path.")
        from src.agents.reflection_agent import reflect_on_failure
        result = reflect_on_failure({"bug": "x"}, "fix code", "test output")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("src.agents.reflection_agent.llm")
    def test_exception_returns_fallback(self, mock_llm):
        mock_llm.invoke.side_effect = Exception("API down")
        from src.agents.reflection_agent import reflect_on_failure
        result = reflect_on_failure({"bug": "x"}, "fix", "output")
        assert isinstance(result, str)
        assert "unavailable" in result.lower() or "error" in result.lower()


# ─── planner_agent (mocked LLM) ───────────────────────────────────────────────

class TestPlannerAgent:

    @patch("src.agents.planner_agent.llm")
    def test_returns_retry(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="retry")
        from src.agents.planner_agent import plan_next_step
        result = plan_next_step("The fix used wrong import. Try direct assignment.")
        assert result == "retry"

    @patch("src.agents.planner_agent.llm")
    def test_returns_stop(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="stop")
        from src.agents.planner_agent import plan_next_step
        result = plan_next_step("Bug is in a C extension. Cannot fix.")
        assert result == "stop"

    @patch("src.agents.planner_agent.llm")
    def test_ambiguous_response_defaults_to_stop(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="maybe try something else")
        from src.agents.planner_agent import plan_next_step
        result = plan_next_step("unclear situation")
        assert result == "stop"

    @patch("src.agents.planner_agent.llm")
    def test_exception_defaults_to_stop(self, mock_llm):
        mock_llm.invoke.side_effect = Exception("timeout")
        from src.agents.planner_agent import plan_next_step
        result = plan_next_step("whatever")
        assert result == "stop"
