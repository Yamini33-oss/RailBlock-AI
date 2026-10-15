"""
===============================================================================
Integration Tests: Member 3 Contract & System Interoperability
===============================================================================
Verifies the integration contract between Member 2 and Member 3 (Optimizer),
multi-window candidate ranking, JSON serializability, and Pydantic validation.
"""

import json
import pytest

from predict_delay import compare_candidate_windows, predict_maintenance_window
from prediction_schema import MaintenanceWindowRequest, PredictionResponse


class TestMember3IntegrationContract:
    """Verifies that Member 3 can import and consume Member 2's prediction engine."""

    @pytest.fixture
    def candidate_windows(self):
        return [
            {
                "request_id": "CAND_NIGHT_01",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-20",
                "proposed_start_time": "01:30",
                "proposed_end_time": "04:30",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": "CAND_MORNING_02",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-20",
                "proposed_start_time": "07:00",
                "proposed_end_time": "10:00",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": "CAND_AFTERNOON_03",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-20",
                "proposed_start_time": "12:30",
                "proposed_end_time": "15:30",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
        ]

    def test_compare_candidate_windows_ranking(self, candidate_windows):
        res = compare_candidate_windows(candidate_windows)

        assert res["total_candidates"] == 3
        assert res["recommended_request_id"] is not None
        assert len(res["ranked_candidates"]) == 3

        # Verify ascending order of disruption score
        scores = [item["prediction"]["disruption_score"] for item in res["ranked_candidates"]]
        assert scores == sorted(scores), "Candidates are not sorted in ascending order of disruption score!"

        # Verify rank indices and recommendation flags
        for i, item in enumerate(res["ranked_candidates"], start=1):
            assert item["rank"] == i
            if i == 1:
                assert item["is_recommended"] is True
                assert item["prediction"]["request_id"] == res["recommended_request_id"]
            else:
                assert item["is_recommended"] is False

    def test_json_serializability(self, candidate_windows):
        res = compare_candidate_windows(candidate_windows)
        # Must serialize cleanly to standard JSON
        json_str = json.dumps(res, indent=2)
        assert len(json_str) > 0
        decoded = json.loads(json_str)
        assert decoded["total_candidates"] == 3

    def test_pydantic_schema_validation(self, candidate_windows):
        # Validate input schema
        pydantic_req = MaintenanceWindowRequest(**candidate_windows[0])
        assert pydantic_req.request_id == "CAND_NIGHT_01"

        # Predict using Pydantic model
        raw_pred = predict_maintenance_window(pydantic_req)

        # Validate output schema
        pydantic_resp = PredictionResponse(**raw_pred)
        assert pydantic_resp.request_id == "CAND_NIGHT_01"
        assert pydantic_resp.disruption_score > 0
