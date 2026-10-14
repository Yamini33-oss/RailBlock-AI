"""Comprehensive end-to-end tests covering all 15 scenarios mandated in the master prompt.

Scenarios:
 1. A request with one valid candidate window.
 2. Several feasible candidates with different predicted disruption.
 3. A high-traffic period versus a lower-traffic period.
 4. A train movement overlapping a candidate window.
 5. A window shorter than the required duration.
 6. A required resource that is unavailable.
 7. A request outside the planning horizon.
 8. An invalid negative duration.
 9. An empty or incomplete dataset.
10. A prediction-service failure.
11. A Member 4 validation conflict followed by a valid alternative.
12. No candidate passes validation.
13. A solver-infeasible scenario.
14. A request crossing midnight or spanning multiple dates.
15. An end-to-end request-to-recommendation flow.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from optimizer.data_adapter import BaselineDelayPredictor, Member2PredictorAdapter
from optimizer.exceptions import PredictionServiceError
from optimizer.schemas import (
    MaintenancePriority,
    MaintenanceRequest,
    OptimizationStatus,
    PlanningConfig,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    TrafficDensityCategory,
    TrafficDensityRecord,
    TrainSchedule,
    ValidationStatus,
)
from optimizer.service import optimize_maintenance_window
from optimizer.validation_client import MockMember4Validator

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# 1. A request with one valid candidate window
# ---------------------------------------------------------------------------
def test_scenario_01_single_valid_candidate_window(sample_resources):
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )
    resp = optimize_maintenance_window(
        request=req,
        input_data={"resource_data": sample_resources},
        config=PlanningConfig(step_minutes=30),
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    assert resp.recommendation is not None
    assert resp.recommendation.start_time == datetime(2026, 10, 15, 11, 0, tzinfo=IST)
    assert resp.recommendation.end_time == datetime(2026, 10, 15, 12, 0, tzinfo=IST)
    assert resp.recommendation.duration_minutes == 60
    assert len(resp.alternatives) == 0


# ---------------------------------------------------------------------------
# 2. Several feasible candidates with different predicted disruption
# ---------------------------------------------------------------------------
def test_scenario_02_several_feasible_candidates_different_disruption(
    sample_train_schedules, sample_traffic_density, sample_resources
):
    # Horizon 08:00 to 14:00 (6 hours)
    # Windows around 08:00-09:30 overlap Rajdhani/Shatabdi (high disruption)
    # Window 11:00-12:00 has zero overlapping trains and low traffic (low disruption)
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-02",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )
    resp = optimize_maintenance_window(
        request=req,
        input_data={
            "train_data": sample_train_schedules,
            "traffic_data": sample_traffic_density,
            "resource_data": sample_resources,
        },
        config=PlanningConfig(step_minutes=30, max_alternatives=5),
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    assert resp.recommendation is not None
    # Best window should be in the low disruption midday period (10:30, 11:00, 11:30, 12:00)
    assert resp.recommendation.start_time.hour in (10, 11, 12)
    assert resp.estimated_impact.affected_train_count == 0
    # There should be ranked alternatives
    assert len(resp.alternatives) > 0
    # Alternatives should have objective scores greater than or equal to recommended
    rec_score = resp.solver.objective_score
    for alt in resp.alternatives:
        assert alt.objective_score >= rec_score


# ---------------------------------------------------------------------------
# 3. A high-traffic period versus a lower-traffic period
# ---------------------------------------------------------------------------
def test_scenario_03_high_traffic_vs_lower_traffic(sample_resources):
    traffic = [
        TrafficDensityRecord(
            track_section_id="SEC-01",
            start_time=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            end_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
            density_score=0.90,  # High traffic
            density_category=TrafficDensityCategory.HIGH,
        ),
        TrafficDensityRecord(
            track_section_id="SEC-01",
            start_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
            end_time=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
            density_score=0.10,  # Low traffic
            density_category=TrafficDensityCategory.LOW,
        ),
    ]
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-03",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )

    resp = optimize_maintenance_window(
        request=req,
        input_data={"traffic_data": traffic, "resource_data": sample_resources},
        config=PlanningConfig(step_minutes=30),
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    # Should choose a window starting at 10:00 or later (during the 0.10 density period)
    assert resp.recommendation.start_time >= datetime(2026, 10, 15, 10, 0, tzinfo=IST)
    assert resp.estimated_impact.traffic_density <= 0.20


# ---------------------------------------------------------------------------
# 4. A train movement overlapping a candidate window
# ---------------------------------------------------------------------------
def test_scenario_04_train_movement_overlapping_candidate(sample_resources):
    # Only two candidate slots: 08:00-09:00 (overlaps train 12951) and 09:00-10:00 (clean)
    trains = [
        TrainSchedule(
            train_number="12951",
            track_section_id="SEC-01",
            scheduled_arrival=datetime(2026, 10, 15, 8, 15, tzinfo=IST),
            scheduled_departure=datetime(2026, 10, 15, 8, 45, tzinfo=IST),
            train_type="RAJDHANI",
        )
    ]
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-04",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )

    resp = optimize_maintenance_window(
        request=req,
        input_data={"train_data": trains, "resource_data": sample_resources},
        config=PlanningConfig(step_minutes=60),
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    # Must select 09:00-10:00 over 08:00-09:00 to avoid overlapping train 12951
    assert resp.recommendation.start_time == datetime(2026, 10, 15, 9, 0, tzinfo=IST)
    assert resp.estimated_impact.affected_train_count == 0


# ---------------------------------------------------------------------------
# 5. A window shorter than the required duration
# ---------------------------------------------------------------------------
def test_scenario_05_window_shorter_than_required_duration():
    # If a candidate window could somehow be shorter than duration, candidate_generator rejects it,
    # or if horizon < required duration, schema / candidate generator catches it.
    # Case: Request where horizon is 50 mins but required duration is 60 mins -> rejected by schema
    with pytest.raises(Exception):
        MaintenanceRequest(
            request_id="MR-SCENARIO-05",
            track_section_id="SEC-01",
            planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            planning_end=datetime(2026, 10, 15, 8, 50, tzinfo=IST),
            required_duration_minutes=60,
        )


# ---------------------------------------------------------------------------
# 6. A required resource that is unavailable
# ---------------------------------------------------------------------------
def test_scenario_06_required_resource_unavailable():
    # Resource is available only 14:00 to 18:00, but request is 08:00 to 12:00
    resources = [
        ResourceAvailabilityRecord(
            resource_id="SPECIAL_CRANE_01",
            available_start=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
            available_end=datetime(2026, 10, 15, 18, 0, tzinfo=IST),
            quantity_available=1,
        )
    ]
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-06",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["SPECIAL_CRANE_01"],
    )

    resp = optimize_maintenance_window(
        request=req,
        input_data={"resource_data": resources},
        config=PlanningConfig(step_minutes=30),
    )

    assert resp.status == OptimizationStatus.NO_FEASIBLE_WINDOW
    assert resp.recommendation is None
    assert any("SPECIAL_CRANE_01" in r.reasons[0] for r in resp.rejected_candidates)


# ---------------------------------------------------------------------------
# 7. A request outside the planning horizon
# ---------------------------------------------------------------------------
def test_scenario_07_request_outside_planning_horizon():
    # earliest_start_time earlier than planning_start
    with pytest.raises(Exception):
        MaintenanceRequest(
            request_id="MR-SCENARIO-07",
            track_section_id="SEC-01",
            planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
            required_duration_minutes=60,
            earliest_start_time=datetime(2026, 10, 15, 7, 0, tzinfo=IST),
        )


# ---------------------------------------------------------------------------
# 8. An invalid negative duration
# ---------------------------------------------------------------------------
def test_scenario_08_invalid_negative_duration():
    payload = {
        "request_id": "MR-SCENARIO-08",
        "track_section_id": "SEC-01",
        "planning_start": "2026-10-15T08:00:00+05:30",
        "planning_end": "2026-10-15T12:00:00+05:30",
        "required_duration_minutes": -45,
    }
    resp = optimize_maintenance_window(request=payload)
    assert resp.status == OptimizationStatus.INVALID_REQUEST
    assert "greater than 0" in resp.explanation[0]


# ---------------------------------------------------------------------------
# 9. An empty or incomplete dataset
# ---------------------------------------------------------------------------
def test_scenario_09_empty_or_incomplete_dataset(sample_resources):
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-09",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )
    # Empty train schedule and traffic density provided; engine must handle cleanly
    resp = optimize_maintenance_window(
        request=req,
        input_data={"train_data": [], "traffic_data": [], "resource_data": sample_resources},
        config=PlanningConfig(step_minutes=30),
    )
    assert resp.status == OptimizationStatus.RECOMMENDED
    assert resp.recommendation is not None
    assert resp.estimated_impact.affected_train_count == 0


# ---------------------------------------------------------------------------
# 10. A prediction-service failure
# ---------------------------------------------------------------------------
def test_scenario_10_prediction_service_failure(sample_resources):
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-10",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )

    def failing_predictor(cand, trains, traffic):
        raise RuntimeError("Member 2 ML Model Connection Timeout")

    adapter = Member2PredictorAdapter(predictor_callable=failing_predictor, fallback_to_baseline=False)

    resp = optimize_maintenance_window(
        request=req,
        input_data={"resource_data": sample_resources},
        config=PlanningConfig(step_minutes=30),
        predictor=adapter,
    )
    assert resp.status == OptimizationStatus.PREDICTION_UNAVAILABLE
    assert "Member 2 ML Model Connection Timeout" in resp.explanation[0]


# ---------------------------------------------------------------------------
# 11. A Member 4 validation conflict followed by a valid alternative
# ---------------------------------------------------------------------------
def test_scenario_11_validation_conflict_then_valid_alternative(
    sample_train_schedules, sample_traffic_density, sample_resources
):
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-11",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 13, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )

    # In our generator, CW-006 is 10:30-11:30 (rank #1).
    # Configure validator to reject CW-006 with CONFLICT!
    validator = MockMember4Validator(rejected_candidate_ids=["CW-006"])

    resp = optimize_maintenance_window(
        request=req,
        input_data={
            "train_data": sample_train_schedules,
            "traffic_data": sample_traffic_density,
            "resource_data": sample_resources,
        },
        config=PlanningConfig(step_minutes=30),
        validator=validator,
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    assert resp.recommendation is not None
    # Recommendation must NOT be CW-006
    assert resp.validation.validation_attempts >= 2
    assert any("CW-006" in rej.candidate_id for rej in resp.rejected_candidates)
    assert any("rejected by Member 4 conflict validator" in exp for exp in resp.explanation)


# ---------------------------------------------------------------------------
# 12. No candidate passes validation
# ---------------------------------------------------------------------------
def test_scenario_12_no_candidate_passes_validation(sample_resources):
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-12",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["TRACK_TEAM_A"],
    )
    # Validator rejects ALL candidates with CONFLICT
    def reject_all_fn(cand_eval):
        from optimizer.schemas import ValidationResult
        return ValidationResult(
            candidate_id=cand_eval.candidate_id,
            status=ValidationStatus.CONFLICT,
            reason="Mandatory system route lock in effect.",
            validator_name="MockStrictValidator",
        )

    validator = MockMember4Validator(custom_rule_fn=reject_all_fn)

    resp = optimize_maintenance_window(
        request=req,
        input_data={"resource_data": sample_resources},
        config=PlanningConfig(step_minutes=30),
        validator=validator,
    )

    assert resp.status == OptimizationStatus.NO_FEASIBLE_WINDOW
    assert resp.recommendation is None
    assert any("passed Member 4 operational conflict validation" in exp for exp in resp.explanation)


# ---------------------------------------------------------------------------
# 13. A solver-infeasible scenario
# ---------------------------------------------------------------------------
def test_scenario_13_solver_infeasible_scenario():
    # Section is closed for the entire horizon
    sections = [
        SectionAvailabilityRecord(
            track_section_id="SEC-01",
            available_start=datetime(2026, 10, 15, 0, 0, tzinfo=IST),
            available_end=datetime(2026, 10, 16, 0, 0, tzinfo=IST),
            is_blocked=True,
            block_reason="Emergency Track Bed Re-laying",
        )
    ]
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-13",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
    )

    resp = optimize_maintenance_window(
        request=req,
        input_data={"section_data": sections},
        config=PlanningConfig(step_minutes=30),
    )

    assert resp.status == OptimizationStatus.NO_FEASIBLE_WINDOW
    assert resp.solver.status.value == "INFEASIBLE"
    assert resp.recommendation is None


# ---------------------------------------------------------------------------
# 14. A request crossing midnight or spanning multiple dates
# ---------------------------------------------------------------------------
def test_scenario_14_request_crossing_midnight():
    resources = [
        ResourceAvailabilityRecord(
            resource_id="NIGHT_GANG_01",
            available_start=datetime(2026, 10, 15, 20, 0, tzinfo=IST),
            available_end=datetime(2026, 10, 16, 8, 0, tzinfo=IST),
            quantity_available=2,
        )
    ]
    req = MaintenanceRequest(
        request_id="MR-SCENARIO-14",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 22, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 16, 4, 0, tzinfo=IST),
        required_duration_minutes=120,
        required_resources=["NIGHT_GANG_01"],
    )

    resp = optimize_maintenance_window(
        request=req,
        input_data={"resource_data": resources},
        config=PlanningConfig(step_minutes=60),
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    assert resp.recommendation is not None
    assert resp.recommendation.duration_minutes == 120
    # Window spans across midnight (e.g. 22:00 to 00:00 or 23:00 to 01:00)
    assert resp.recommendation.start_time >= req.planning_start
    assert resp.recommendation.end_time <= req.planning_end


# ---------------------------------------------------------------------------
# 15. An end-to-end request-to-recommendation flow
# ---------------------------------------------------------------------------
def test_scenario_15_full_end_to_end_flow(
    sample_train_schedules, sample_traffic_density, sample_resources, sample_sections
):
    req = MaintenanceRequest(
        request_id="MR-E2E-MASTER",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
        maintenance_priority=MaintenancePriority.HIGH,
        required_resources=["TRACK_TEAM_A"],
    )

    resp = optimize_maintenance_window(
        request=req,
        input_data={
            "train_data": sample_train_schedules,
            "traffic_data": sample_traffic_density,
            "resource_data": sample_resources,
            "section_data": sample_sections,
        },
        config=PlanningConfig(step_minutes=15, max_alternatives=5),
        predictor=BaselineDelayPredictor(),
        validator=MockMember4Validator(),
    )

    # 1. Status is RECOMMENDED
    assert resp.status == OptimizationStatus.RECOMMENDED
    assert resp.request_id == "MR-E2E-MASTER"

    # 2. Recommendation details
    assert resp.recommendation is not None
    assert resp.recommendation.track_section_id == "SEC-01"
    assert resp.recommendation.duration_minutes == 60

    # 3. Estimated impact
    assert resp.estimated_impact is not None
    assert resp.estimated_impact.predicted_delay_minutes is not None
    assert resp.estimated_impact.traffic_density is not None

    # 4. Member 4 validation passed
    assert resp.validation is not None
    assert resp.validation.status == ValidationStatus.VALID
    assert resp.validation.validation_attempts >= 1

    # 5. Solver metadata
    assert resp.solver is not None
    assert resp.solver.status.value in ("OPTIMAL", "FEASIBLE")
    assert resp.solver.objective_score is not None

    # 6. Ranked alternatives
    assert len(resp.alternatives) > 0
    assert resp.alternatives[0].rank == 1

    # 7. Human-readable explanation
    assert len(resp.explanation) >= 3
    assert any("Recommended maintenance block" in exp for exp in resp.explanation)
    assert any("Optimization score" in exp for exp in resp.explanation)
