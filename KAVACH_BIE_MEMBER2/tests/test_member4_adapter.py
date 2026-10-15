"""
===============================================================================
Unit Tests: Member 4 Conflict Validation Adapter (adapters/member4_adapter.py)
===============================================================================
Tests operational conflict handoff payload, timetable overlap extraction,
and architectural boundary enforcement.
"""

import pytest

from adapters.member4_adapter import Member4ValidationAdapter
from prediction_schema import Member4ValidationPayload


class TestMember4ValidationAdapter:
    """Tests for Member 4 validation adapter."""

    @pytest.fixture
    def maintenance_req(self):
        return {
            "request_id": "REQ_M4_TEST",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-25",
            "proposed_start_time": "01:30",
            "proposed_end_time": "04:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        }

    def test_get_validation_payload_structure(self, maintenance_req):
        payload = Member4ValidationAdapter.get_validation_payload(maintenance_req)

        assert isinstance(payload, Member4ValidationPayload)
        assert payload.request_id == "REQ_M4_TEST"
        assert payload.track_section == "SEC_NDLS_CNB"
        assert payload.affected_train_count >= 0
        assert isinstance(payload.conflicting_trains, list)
        assert payload.predicted_baseline_delay_minutes >= 0.0
        assert payload.maintenance_exposure_score >= 0.0
        assert "Member 4 must independently certify" in payload.disclaimer

    def test_extract_conflicting_train_list(self, maintenance_req):
        conflicts = Member4ValidationAdapter.extract_conflicting_train_list(maintenance_req)
        assert isinstance(conflicts, list)
        for train in conflicts:
            assert "train_number" in train
            assert "train_name" in train
            assert "scheduled_arrival" in train
            assert "scheduled_departure" in train
