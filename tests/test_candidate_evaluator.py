"""Tests for candidate evaluator and constraint checks."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from optimizer.candidate_evaluator import evaluate_candidate
from optimizer.data_adapter import BaselineDelayPredictor
from optimizer.objective import ObjectiveCalculator
from optimizer.schemas import (
    CandidateWindow,
    MaintenancePriority,
    MaintenanceRequest,
    ObjectiveWeights,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    TrafficDensityCategory,
    TrafficDensityRecord,
    TrainSchedule,
)

IST = ZoneInfo("Asia/Kolkata")


def test_train_overlap_detected(sample_train_schedules, sample_traffic_density):
    # Candidate overlaps Train 12951 (08:15 to 08:45)
    cand = CandidateWindow(
        candidate_id="CW-TEST-01",
        track_section_id="SEC-01",
        start_time=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        end_time=datetime(2026, 10, 15, 9, 0, tzinfo=IST),
        duration_minutes=60,
    )
    req = MaintenanceRequest(
        request_id="MR-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
    )

    ev = evaluate_candidate(
        candidate=cand,
        request=req,
        train_data=sample_train_schedules,
        traffic_data=sample_traffic_density,
        prediction_service=BaselineDelayPredictor(),
    )

    assert ev.is_feasible is True
    assert "12951" in ev.affected_trains
    assert ev.affected_train_count == 1
    assert ev.predicted_delay_minutes > 0


def test_clean_window_zero_affected_trains(sample_train_schedules, sample_traffic_density):
    # Midday window 11:00 to 12:00 has NO scheduled trains on SEC-01
    cand = CandidateWindow(
        candidate_id="CW-TEST-CLEAN",
        track_section_id="SEC-01",
        start_time=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        end_time=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        duration_minutes=60,
    )
    req = MaintenanceRequest(
        request_id="MR-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
    )

    ev = evaluate_candidate(
        candidate=cand,
        request=req,
        train_data=sample_train_schedules,
        traffic_data=sample_traffic_density,
        prediction_service=BaselineDelayPredictor(),
    )

    assert ev.is_feasible is True
    assert ev.affected_train_count == 0
    assert len(ev.affected_trains) == 0
    # Minimal delay for zero affected trains
    assert ev.predicted_delay_minutes < 5.0


def test_missing_required_resource_marks_infeasible():
    cand = CandidateWindow(
        candidate_id="CW-TEST-RES",
        track_section_id="SEC-01",
        start_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        end_time=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        duration_minutes=60,
    )
    # Requires SPECIAL_CRANE_99 which is not in resources
    req = MaintenanceRequest(
        request_id="MR-RES-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["SPECIAL_CRANE_99"],
    )

    resources = [
        ResourceAvailabilityRecord(
            resource_id="TRACK_TEAM_A",
            available_start=datetime(2026, 10, 15, 6, 0, tzinfo=IST),
            available_end=datetime(2026, 10, 15, 18, 0, tzinfo=IST),
            quantity_available=1,
        )
    ]

    ev = evaluate_candidate(
        candidate=cand,
        request=req,
        train_data=[],
        traffic_data=[],
        resource_data=resources,
    )

    assert ev.is_feasible is False
    assert ev.resource_feasible is False
    assert any("SPECIAL_CRANE_99" in viol for viol in ev.hard_violations)


def test_section_closure_marks_infeasible():
    cand = CandidateWindow(
        candidate_id="CW-TEST-SEC",
        track_section_id="SEC-01",
        start_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        end_time=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        duration_minutes=60,
    )
    req = MaintenanceRequest(
        request_id="MR-SEC-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
    )

    sections = [
        SectionAvailabilityRecord(
            track_section_id="SEC-01",
            available_start=datetime(2026, 10, 15, 9, 30, tzinfo=IST),
            available_end=datetime(2026, 10, 15, 10, 30, tzinfo=IST),
            is_blocked=True,
            block_reason="Emergency Signal Cable Splicing",
        )
    ]

    ev = evaluate_candidate(
        candidate=cand,
        request=req,
        train_data=[],
        traffic_data=[],
        section_data=sections,
    )

    assert ev.is_feasible is False
    assert ev.section_feasible is False
    assert any("Emergency Signal Cable Splicing" in viol for viol in ev.hard_violations)


def test_high_traffic_period_vs_lower_traffic_period():
    # Cand 1: Morning peak 08:30-09:30 (traffic density 0.85)
    cand_high = CandidateWindow(
        candidate_id="CW-HIGH",
        track_section_id="SEC-01",
        start_time=datetime(2026, 10, 15, 8, 30, tzinfo=IST),
        end_time=datetime(2026, 10, 15, 9, 30, tzinfo=IST),
        duration_minutes=60,
    )
    # Cand 2: Midday lull 11:30-12:30 (traffic density 0.15)
    cand_low = CandidateWindow(
        candidate_id="CW-LOW",
        track_section_id="SEC-01",
        start_time=datetime(2026, 10, 15, 11, 30, tzinfo=IST),
        end_time=datetime(2026, 10, 15, 12, 30, tzinfo=IST),
        duration_minutes=60,
    )

    req = MaintenanceRequest(
        request_id="MR-COMP-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
    )

    traffic = [
        TrafficDensityRecord(
            track_section_id="SEC-01",
            start_time=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            end_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
            density_score=0.85,
        ),
        TrafficDensityRecord(
            track_section_id="SEC-01",
            start_time=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
            end_time=datetime(2026, 10, 15, 13, 0, tzinfo=IST),
            density_score=0.15,
        ),
    ]

    calc = ObjectiveCalculator(ObjectiveWeights())
    ev_high = evaluate_candidate(cand_high, req, [], traffic, calculator=calc)
    ev_low = evaluate_candidate(cand_low, req, [], traffic, calculator=calc)

    # Low traffic candidate must have a lower (better) objective score
    assert ev_low.objective_score < ev_high.objective_score
    assert ev_low.traffic_density_score < ev_high.traffic_density_score
