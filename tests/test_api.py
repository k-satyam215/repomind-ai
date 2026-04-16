"""
Tests for FastAPI routes using TestClient.
LLM and git calls are mocked.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestHealthRoutes:

    def test_root(self):
        res = client.get("/")
        assert res.status_code == 200
        assert "RepoMind" in res.json()["message"]

    def test_health(self):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


class TestAnalyzeRoute:

    def test_invalid_url_rejected(self):
        res = client.post("/analyze", json={"repo_url": "https://notgithub.com/owner/repo"})
        assert res.status_code == 422

    def test_empty_url_rejected(self):
        res = client.post("/analyze", json={"repo_url": ""})
        assert res.status_code == 422

    @patch("src.api.routes.analyze_repository")
    def test_successful_analysis(self, mock_analyze):
        mock_analyze.return_value = {
            "analysis": "FastAPI project",
            "issues": [],
            "repo_path": "/tmp/repomind_test",
            "dependency_map": {},
            "repo_url": "https://github.com/owner/repo"
        }

        res = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo"})
        assert res.status_code == 200
        data = res.json()
        assert data["analysis"] == "FastAPI project"
        assert data["issues"] == []


class TestDiffRoute:

    def test_basic_diff(self):
        res = client.post("/diff", json={
            "old": "x = 1\ny = 2",
            "new": "x = 1\ny = 3",
            "filename": "test.py"
        })
        assert res.status_code == 200
        assert "-y = 2" in res.json()["diff"]
        assert "+y = 3" in res.json()["diff"]

    def test_identical_returns_empty_diff(self):
        res = client.post("/diff", json={"old": "x = 1", "new": "x = 1"})
        assert res.status_code == 200
        assert res.json()["diff"] == ""


class TestFixRoute:

    def test_missing_file_returns_404(self, tmp_path):
        res = client.post("/fix", json={
            "repo_path": str(tmp_path),
            "file": "nonexistent.py",
            "bug": {"bug": "x", "impact": "y", "fix_hint": "z"}
        })
        assert res.status_code == 404

    @patch("src.api.routes.generate_fix")
    def test_successful_fix(self, mock_fix, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("x = 1", encoding="utf-8")

        mock_fix.return_value = "x = 999"

        res = client.post("/fix", json={
            "repo_path": str(tmp_path),
            "file": "target.py",
            "bug": {"bug": "wrong value", "impact": "high", "fix_hint": "change to 999"}
        })

        assert res.status_code == 200
        data = res.json()
        assert data["old"] == "x = 1"
        assert data["new"] == "x = 999"
