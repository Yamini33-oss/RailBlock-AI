"""
===============================================================================
Unit Tests: Prediction Engine & Disruption Scoring (predict_delay.py)
===============================================================================
Tests single-window delay prediction, schedule overlap calculation,
disruption scoring formulas, risk categorization, and uncertainty bounds.
"""

import pytest
import pandas as pd

from config import PRIORITY_MULTIPLIERS
from predict_delay import (
    calculate_affected_trains,
    calculate_disruption_score,
    classify_risk_category,
    predict_maintenance_window,
)


class TestDisruptionScoring:
    """Tests for disruption scoring mathematics and risk categorization."""

    def test_disruption_score_calculation(self):
        # Delay=20.0, Density=0.7, Trains=4, Duration=180, Priority="MEDIUM" (mult=1.0)
        # Score = (20*0.35) + (0.7*20*0.25) + (4*10*0.25) + ((180/60)*5*0.15) * 1.0
        #       = 7.0 + 3.5 + 10.0 + 2.25 = 22.75 -> 22.75
        score = calculate_disruption_score(
            predicted_delay_minutes=20.0,
            traffic_density=0.7,
            affected_train_count=4,
            duration_minutes=180.0,
            priority="MEDIUM",
        )
        assert score == 22.75

    def test_priority_multiplier_impact(self):
        score_low = calculate_disruption_score(15.0, 0.5, 2, 120.0, "LOW")
        score_crit = calculate_disruption_score(15.0, 0.5, 2, 120.0, "CRITICAL")
        assert score_crit > score_low
        assert round(score_crit / score_low, 2) == round(
            PRIORITY_MULTIPLIERS["CRITICAL"] / PRIORITY_MULTIPLIERS["LOW"], 2
        )

    def test_risk_category_classification(self):
        assert classify_risk_category(15.0) == "LOW"
        assert classify_risk_category(35.0) == "MEDIUM"
        assert classify_risk_category(60.0) == "HIGH"
        assert classify_risk_category(95.0) == "CRITICAL"


class TestAffectedTrainsCalculation:
    """Tests for timetable overlap counting."""

    @pytest.fixture
    def sample_schedules(self):
        return pd.DataFrame(
            [
                {
                    "train_number": "T1",
                    "track_section": "SEC_TEST",
                    "scheduled_arrival": "01:00",
                    "scheduled_departure": "03:00",
                },
                {
                    "train_number": "T2",
                    "track_section": "SEC_TEST",
                    "scheduled_arrival": "07:00",
                    "scheduled_departure": "09:00",
                },
                {
                    "train_number": "T3",
                    "track_section": "OTHER_SEC",
                    "scheduled_arrival": "02:00",
                    "scheduled_departure": "04:00",
                },
            ]
        )

    def test_affected_trains_overlap(self, sample_schedules):
        # Window 01:30 to 03:30 on SEC_TEST should overlap with T1, not T2 or T3
        count = calculate_affected_trains(
            track_section="SEC_TEST",
            start_time_str="01:30",
            end_time_str="03:30",
            schedules_df=sample_schedules,
            buffer_minutes=15,
        )
        assert count == 1


class TestSingleWindowPrediction:
    """Tests for predict_maintenance_window."""

    def test_predict_valid_request(self):
        req = {
            "request_id": "REQ_TEST_VALID",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-20",
            "proposed_start_time": "02:00",
            "proposed_end_time": "05:00",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        }
        res = predict_maintenance_window(req)

        assert res["request_id"] == "REQ_TEST_VALID"
        assert res["predicted_delay_minutes"] >= 0.0
        assert res["affected_train_count"] >= 0
        assert res["disruption_score"] >= 0.0
        assert res["risk_category"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert "uncertainty" in res
        assert "explanation" in res
        assert isinstance(res["explanation"], list)
        assert len(res["explanation"]) > 0

    def test_predict_invalid_request_raises(self):
        bad_req = {
            "request_id": "REQ_BAD",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-20",
            "proposed_start_time": "02:00",
            "proposed_end_time": "05:00",
            "required_duration_minutes": -50.0,  # Negative duration
        }
        with pytest.raises(ValueError):
            predict_maintenance_window(bad_req)
