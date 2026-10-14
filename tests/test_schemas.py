"""Tests for Pydantic input/output schemas and domain validations."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from pydantic import ValidationError

from optimizer.schemas import (
    MaintenancePriority,
    MaintenanceRequest,
    ObjectiveWeights,
    PlanningConfig,
    TrainSchedule,
)

IST = ZoneInfo("Asia/Kolkata")


def test_valid_maintenance_request():
    req = MaintenanceRequest(
        request_id="MR-VALID-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
        maintenance_priority=MaintenancePriority.HIGH,
    )
    assert req.request_id == "MR-VALID-01"
    assert req.required_duration_minutes == 60
    assert req.maintenance_priority == MaintenancePriority.HIGH


def test_negative_or_zero_duration_rejected():
    with pytest.raises(ValidationError) as exc:
        MaintenanceRequest(
            request_id="MR-INV-01",
            track_section_id="SEC-01",
            planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
            required_duration_minutes=0,
        )
    assert "greater than 0" in str(exc.value)

    with pytest.raises(ValidationError) as exc2:
        MaintenanceRequest(
            request_id="MR-INV-02",
            track_section_id="SEC-01",
            planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
            required_duration_minutes=-30,
        )
    assert "greater than 0" in str(exc2.value)


def test_reversed_planning_horizon_rejected():
    with pytest.raises(ValidationError) as exc:
        MaintenanceRequest(
            request_id="MR-INV-03",
            track_section_id="SEC-01",
            planning_start=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
            planning_end=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            required_duration_minutes=60,
        )
    assert "must be strictly after planning_start" in str(exc.value)


def test_duration_exceeding_horizon_rejected():
    with pytest.raises(ValidationError) as exc:
        MaintenanceRequest(
            request_id="MR-INV-04",
            track_section_id="SEC-01",
            planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            planning_end=datetime(2026, 10, 15, 9, 0, tzinfo=IST),
            required_duration_minutes=120,
        )
    assert "exceeds total planning horizon" in str(exc.value)


def test_earliest_latest_bounds_validation():
    # Earliest start earlier than planning_start
    with pytest.raises(ValidationError) as exc:
        MaintenanceRequest(
            request_id="MR-INV-05",
            track_section_id="SEC-01",
            planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
            planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
            required_duration_minutes=60,
            earliest_start_time=datetime(2026, 10, 15, 7, 0, tzinfo=IST),
        )
    assert "earliest_start_time cannot be earlier than planning_start" in str(exc.value)


def test_train_schedule_departure_before_arrival_rejected():
    with pytest.raises(ValidationError) as exc:
        TrainSchedule(
            train_number="12951",
            track_section_id="SEC-01",
            scheduled_arrival=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
            scheduled_departure=datetime(2026, 10, 15, 9, 0, tzinfo=IST),
        )
    assert "scheduled_departure" in str(exc.value)


def test_objective_weights_normalization():
    weights = ObjectiveWeights(
        weight_delay=2.0,
        weight_trains=1.0,
        weight_traffic_density=1.0,
        weight_slack_duration=0.0,
        weight_priority_urgency=1.0,
    )
    norm = weights.normalized()
    total = sum(norm.values())
    assert pytest.approx(total, 0.001) == 1.0
    assert pytest.approx(norm["weight_delay"], 0.001) == 2.0 / 5.0
