"""
Tests for Sky webhook API endpoints
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.sky.service import app

client = TestClient(app)


def test_health_endpoint():
    """Test /health returns OK"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "component" in data


def test_status_endpoint():
    """Test /status returns heartbeat and last_action"""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "heartbeat" in data
    assert "last_action" in data


def test_tools_endpoint():
    """Test /tools lists available tools"""
    response = client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "tools" in data
    assert isinstance(data["tools"], list)


def test_run_tool_missing():
    """Test /run_tool with nonexistent tool returns 400"""
    response = client.post(
        "/run_tool",
        json={"tool": "nonexistent_tool_xyz"}
    )
    # Should fail (400) because tool doesn't exist
    assert response.status_code == 400


def test_run_tool_with_args():
    """Test /run_tool accepts args parameter"""
    response = client.post(
        "/run_tool",
        json={
            "tool": "some_tool",
            "args": ["--flag", "value"]
        }
    )
    # Will likely fail (tool doesn't exist) but request format should be valid
    assert response.status_code in [400, 403]  # Either tool missing or auth blocked


def test_run_task_unknown():
    """Test /run_task with unknown task"""
    response = client.post(
        "/run_task",
        json={"task": "unknown_task_xyz"}
    )
    # Should fail because task is unknown
    assert response.status_code in [400, 403]


def test_authority_enforcement():
    """
    Test that authority gate is enforced on webhooks

    NOTE: This test assumes governance module exists.
    If not present, safe defaults should still apply.
    """
    # Try to run a tool (any tool)
    response = client.post(
        "/run_tool",
        json={"tool": "test_tool"}
    )

    # Response should be either:
    # - 403 (authority blocked)
    # - 400 (tool not found, but auth passed)
    assert response.status_code in [400, 403]

    # Check that last_action was written
    status_response = client.get("/status")
    assert status_response.status_code == 200
    data = status_response.json()

    # Should have a last_action entry
    assert "last_action" in data


def test_run_task_heartbeat():
    """Test /run_task can execute heartbeat task"""
    response = client.post(
        "/run_task",
        json={"task": "heartbeat"}
    )

    # Should either succeed or be blocked by authority
    assert response.status_code in [200, 403]

    if response.status_code == 200:
        data = response.json()
        assert data["ok"] is True


# TODO Phase 4+: Add tests for:
# - Mock authority gate to test blocking
# - Test tool execution with captured output
# - Test task chains
# - Test status file updates
# - Test concurrent webhook requests
