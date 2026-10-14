"""Tests for FastAPI endpoints and Member 5 integration contracts."""

from fastapi.testclient import TestClient
import pytest

from optimizer.api import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/optimization/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "Google OR-Tools CP-SAT" in data["solver"]
    assert data["solver_readiness"] == "READY"


def test_recommend_endpoint_valid_request():
    payload = {
        "request_id": "MR-API-001",
        "track_section_id": "SEC-01",
        "planning_start": "2026-10-15T08:00:00+05:30",
        "planning_end": "2026-10-15T18:00:00+05:30",
        "required_duration_minutes": 60,
        "maintenance_priority": "HIGH",
        "required_resources": ["TRACK_TEAM_A"],
    }
    response = client.post("/api/optimization/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "RECOMMENDED"
    assert data["request_id"] == "MR-API-001"
    assert data["recommendation"]["track_section_id"] == "SEC-01"
    assert data["recommendation"]["duration_minutes"] == 60
    assert data["validation"]["status"] == "VALID"
    assert len(data["alternatives"]) >= 1
    assert len(data["explanation"]) >= 1


def test_recommend_endpoint_invalid_request():
    payload = {
        "request_id": "MR-API-INV",
        "track_section_id": "SEC-01",
        "planning_start": "2026-10-15T18:00:00+05:30",
        "planning_end": "2026-10-15T08:00:00+05:30",  # Reversed horizon
        "required_duration_minutes": 60,
    }
    response = client.post("/api/optimization/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INVALID_REQUEST"
    assert data["recommendation"] is None
