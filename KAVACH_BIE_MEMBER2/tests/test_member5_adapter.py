"""
===============================================================================
Unit Tests: Member 5 Dashboard Adapter (adapters/member5_adapter.py)
===============================================================================
Tests mounting and execution of Member 5 APIRouter endpoints.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from adapters.member5_adapter import get_member5_router

sample_app = FastAPI()
sample_app.include_router(get_member5_router(), prefix="/api/v1/delays")
client = TestClient(sample_app)



class TestMember5DashboardAdapter:
    """Tests for Member 5 router and endpoints."""

    def test_router_health(self):
        response = client.get("/api/v1/delays/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_router_model_info(self):
        response = client.get("/api/v1/delays/model-info")
        assert response.status_code == 200
        data = response.json()
        assert "best_model_name" in data
        assert "metrics" in data

    def test_router_data_quality(self):
        response = client.get("/api/v1/delays/data-quality")
        assert response.status_code == 200

    def test_router_predict(self):
        req = {
            "request_id": "M5_REQ_001",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-25",
            "proposed_start_time": "02:00",
            "proposed_end_time": "05:00",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "MEDIUM",
        }
        response = client.post("/api/v1/delays/predict", json=req)
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "M5_REQ_001"
        assert "predicted_baseline_delay_minutes" in data
        assert "maintenance_exposure_score" in data
        assert "data_quality" in data

    def test_router_validation_context(self):
        req = {
            "request_id": "M5_REQ_002",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-25",
            "proposed_start_time": "02:00",
            "proposed_end_time": "05:00",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "MEDIUM",
        }
        response = client.post("/api/v1/delays/validation-context", json=req)
        assert response.status_code == 200
        data = response.json()
        assert "conflicting_trains" in data
        assert "disclaimer" in data
