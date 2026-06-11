"""
Tests for src/observability/metrics — no LLM calls, pure logic.
"""
import os
import json
import time

import pytest

from src.observability.metrics import (
    _default_metrics,
    get_metrics,
    record_bug_detected,
    record_fix_result,
    record_pr_created,
    record_run_start,
    record_run_summary,
    record_stage_latency,
    timed_stage,
    METRICS_PATH,
)


@pytest.fixture(autouse=True)
def clean_metrics(tmp_path, monkeypatch):
    """Redirect metrics file to a temp path for each test."""
    import src.observability.metrics as m
    test_path = str(tmp_path / "metrics.json")
    monkeypatch.setattr(m, "METRICS_PATH", test_path)
    yield
    # cleanup handled by tmp_path


class TestDefaultMetrics:

    def test_default_has_required_keys(self):
        d = _default_metrics()
        assert "total_runs" in d
        assert "total_bugs_detected" in d
        assert "total_fixes_succeeded" in d
        assert "fix_success_by_severity" in d
        assert "retry_distribution" in d
        assert "stage_latency_ms" in d
        assert "recent_runs" in d

    def test_default_values_are_zero(self):
        d = _default_metrics()
        assert d["total_runs"] == 0
        assert d["total_bugs_detected"] == 0
        assert d["total_prs_created"] == 0


class TestRecordFunctions:

    def test_record_run_start_increments(self):
        record_run_start()
        record_run_start()
        m = get_metrics()
        assert m["total_runs"] == 2

    def test_record_bug_detected_increments(self):
        record_bug_detected("critical", "import_error")
        record_bug_detected("high", "runtime_error")
        m = get_metrics()
        assert m["total_bugs_detected"] == 2
        assert m["severity_distribution"]["critical"] == 1
        assert m["severity_distribution"]["high"] == 1

    def test_record_fix_success(self):
        record_fix_result(success=True, retry_count=0, severity="high")
        m = get_metrics()
        assert m["total_fixes_succeeded"] == 1
        assert m["total_fixes_failed"] == 0
        assert m["fix_success_by_severity"]["high"]["success"] == 1

    def test_record_fix_failure(self):
        record_fix_result(success=False, retry_count=2, severity="critical")
        m = get_metrics()
        assert m["total_fixes_failed"] == 1
        assert m["retry_distribution"]["2"] == 1

    def test_record_pr_created(self):
        record_pr_created()
        record_pr_created()
        m = get_metrics()
        assert m["total_prs_created"] == 2

    def test_record_stage_latency(self):
        record_stage_latency("fix_generate", 350.5)
        record_stage_latency("fix_generate", 420.0)
        m = get_metrics()
        samples = m["stage_latency_ms"]["fix_generate"]
        assert 350.5 in samples
        assert 420.0 in samples

    def test_stage_latency_capped_at_100(self, monkeypatch):
        import src.observability.metrics as mod
        monkeypatch.setattr(mod, "METRICS_PATH", mod.METRICS_PATH)  # no-op, just for isolation
        for i in range(110):
            record_stage_latency("test_run", float(i))
        m = get_metrics()
        assert len(m["stage_latency_ms"]["test_run"]) <= 100

    def test_record_run_summary_appears_in_recent(self):
        record_run_summary("run_001", "https://github.com/a/b", bugs=5, fixes=3,
                           success=True, duration_ms=12000)
        m = get_metrics()
        assert len(m["recent_runs"]) == 1
        assert m["recent_runs"][0]["repo"] == "b"
        assert m["recent_runs"][0]["bugs_detected"] == 5

    def test_recent_runs_capped_at_20(self):
        for i in range(25):
            record_run_summary(f"run_{i}", f"https://github.com/a/repo{i}",
                               bugs=1, fixes=1, success=True, duration_ms=1000)
        m = get_metrics()
        assert len(m["recent_runs"]) <= 20


class TestGetMetrics:

    def test_fix_success_rate_computed(self):
        record_fix_result(success=True, retry_count=0)
        record_fix_result(success=True, retry_count=0)
        record_fix_result(success=False, retry_count=1)
        m = get_metrics()
        # 2 success / 3 attempted = 66.7%
        assert abs(m["fix_success_rate_pct"] - 66.7) < 1.0

    def test_fix_success_rate_zero_when_no_attempts(self):
        m = get_metrics()
        assert m["fix_success_rate_pct"] == 0.0

    def test_avg_latency_computed(self):
        record_stage_latency("clone", 1000.0)
        record_stage_latency("clone", 2000.0)
        m = get_metrics()
        assert m["avg_stage_latency_ms"]["clone"] == 1500.0

    def test_avg_latency_none_when_no_samples(self):
        m = get_metrics()
        assert m["avg_stage_latency_ms"]["clone"] is None


class TestTimedStage:

    def test_timed_stage_records_latency(self):
        with timed_stage("analyze"):
            time.sleep(0.01)
        m = get_metrics()
        samples = m["stage_latency_ms"]["analyze"]
        assert len(samples) == 1
        assert samples[0] > 5  # at least 5ms for 10ms sleep

    def test_timed_stage_records_even_on_exception(self):
        try:
            with timed_stage("clone"):
                raise ValueError("test error")
        except ValueError:
            pass
        m = get_metrics()
        assert len(m["stage_latency_ms"]["clone"]) == 1
