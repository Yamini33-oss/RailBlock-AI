"""
===============================================================================
Unit Tests: Member 3 Optimization Adapter (adapters/member3_adapter.py)
===============================================================================
Tests slot evaluation, ranking, filtering by disruption threshold, and Pareto
multi-objective tradeoff analysis.
"""

import pytest

from adapters.member3_adapter import Member3OptimizationAdapter


class TestMember3OptimizationAdapter:
    """Tests for Member 3 optimization helper adapter."""

    @pytest.fixture
    def candidate_slots(self):
        return [
            {
                "request_id": "SLOT_NIGHT_01",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-25",
                "proposed_start_time": "01:30",
                "proposed_end_time": "04:30",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": "SLOT_PEAK_02",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-25",
                "proposed_start_time": "07:00",
                "proposed_end_time": "10:00",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": "SLOT_LONG_NIGHT_03",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-25",
                "proposed_start_time": "00:30",
                "proposed_end_time": "05:30",
                "required_duration_minutes": 300.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": "SLOT_INVALID_04",
                "track_section": "SEC_NDLS_CNB",
                "requested_date": "2026-10-25",
                "proposed_start_time": "01:00",
                "proposed_end_time": "04:00",
                "required_duration_minutes": -40.0,  # Negative duration
                "maintenance_priority": "HIGH",
            },
        ]

    def test_evaluate_slot(self, candidate_slots):
        res = Member3OptimizationAdapter.evaluate_slot(candidate_slots[0])
        assert res["request_id"] == "SLOT_NIGHT_01"
        assert res["predicted_baseline_delay_minutes"] >= 0.0
        assert res["maintenance_exposure_score"] >= 0.0

    def test_rank_candidate_slots(self, candidate_slots):
        ranking = Member3OptimizationAdapter.rank_candidate_slots(candidate_slots)
        assert ranking["total_candidates"] == 4
        assert ranking["feasible_candidates"] == 3
        assert ranking["infeasible_candidates"] == 1
        assert ranking["recommended_request_id"] is not None

        # Infeasible candidate marked clearly
        infeasible_item = next(
            item for item in ranking["ranked_candidates"] if item["candidate_summary"]["request_id"] == "SLOT_INVALID_04"
        )
        assert infeasible_item["is_feasible"] is False
        assert len(infeasible_item["validation_errors"]) > 0

    def test_filter_feasible_slots(self, candidate_slots):
        feasible = Member3OptimizationAdapter.filter_feasible_slots(candidate_slots, max_acceptable_score=50.0)
        assert len(feasible) > 0
        for item in feasible:
            assert item["prediction"]["maintenance_exposure_score"] <= 50.0

    def test_compute_pareto_tradeoffs(self, candidate_slots):
        pareto = Member3OptimizationAdapter.compute_pareto_tradeoffs(candidate_slots)
        assert len(pareto) == 3  # Only feasible candidates analyzed
        assert any(p["is_pareto_optimal"] for p in pareto)
