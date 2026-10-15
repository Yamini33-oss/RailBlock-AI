"""
===============================================================================
Integration Tests: FastAPI REST Endpoints (api.py)
===============================================================================
Tests the HTTP endpoints exposed for Member 5 using FastAPI TestClient:
- GET  /health
- GET  /model-info
- POST /predict
- POST /compare-windows
"""

import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


class TestFastAPIEndpoints:
    """Tests for Member 5 REST adapter."""

    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "KAVACH_BIE_MEMBER2"

    def test_model_info_endpoint(self):
        response = client.get("/model-info")
        assert response.status_code == 200
        data = response.json()
        assert "model_version" in data
        assert "metrics" in data
        assert "features" in data

    def test_predict_endpoint_valid(self):
        payload = {
            "request_id": "API_REQ_001",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-22",
            "proposed_start_time": "02:00",
            "proposed_end_time": "05:00",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "MEDIUM",
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "API_REQ_001"
        assert "predicted_delay_minutes" in data
        assert "disruption_score" in data
        assert "risk_category" in data

    def test_predict_endpoint_invalid_duration(self):
        bad_payload = {
            "request_id": "API_REQ_ERR",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-22",
            "proposed_start_time": "02:00",
            "proposed_end_time": "05:00",
            "required_duration_minutes": -30.0,  # Invalid!
        }
        response = client.post("/predict", json=bad_payload)
        assert response.status_code in [400, 422]

    def test_compare_windows_endpoint(self):
        payload = [
            {
                "request_id": "API_CAND_1",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-22",
                "proposed_start_time": "01:30",
                "proposed_end_time": "04:30",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": "API_CAND_2",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-22",
                "proposed_start_time": "07:30",
                "proposed_end_time": "10:30",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
        ]
        response = client.post("/compare-windows", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_candidates"] == 2
        assert len(data["ranked_candidates"]) == 2
        assert data["recommended_request_id"] in ["API_CAND_1", "API_CAND_2"]
