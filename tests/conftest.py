"""Pytest fixtures for KAVACH BIE Member 3 Optimization Engine."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytest

from optimizer.data_adapter import BaselineDelayPredictor
from optimizer.schemas import (
    MaintenancePriority,
    MaintenanceRequest,
    ObjectiveWeights,
    PlanningConfig,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    TrafficDensityCategory,
    TrafficDensityRecord,
    TrainSchedule,
)
from optimizer.validation_client import MockMember4Validator

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def sample_tz() -> ZoneInfo:
    return IST


@pytest.fixture
def default_config() -> PlanningConfig:
    return PlanningConfig(
        step_minutes=30,
        max_validation_attempts=5,
        solver_time_limit_seconds=5.0,
        max_alternatives=5,
    )


@pytest.fixture
def standard_request(sample_tz) -> MaintenanceRequest:
    return MaintenanceRequest(
        request_id="MR-TEST-001",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=sample_tz),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=sample_tz),
        required_duration_minutes=60,
        maintenance_priority=MaintenancePriority.HIGH,
        required_resources=["TRACK_TEAM_A"],
    )


@pytest.fixture
def sample_train_schedules(sample_tz) -> list[TrainSchedule]:
    return [
        TrainSchedule(
            train_number="12951",
            train_name="Mumbai Rajdhani",
            track_section_id="SEC-01",
            scheduled_arrival=datetime(2026, 10, 15, 8, 15, tzinfo=sample_tz),
            scheduled_departure=datetime(2026, 10, 15, 8, 45, tzinfo=sample_tz),
            train_type="RAJDHANI",
            priority_weight=1.5,
        ),
        TrainSchedule(
            train_number="12001",
            train_name="Shatabdi Express",
            track_section_id="SEC-01",
            scheduled_arrival=datetime(2026, 10, 15, 9, 30, tzinfo=sample_tz),
            scheduled_departure=datetime(2026, 10, 15, 10, 0, tzinfo=sample_tz),
            train_type="EXPRESS",
            priority_weight=1.2,
        ),
        TrainSchedule(
            train_number="54301",
            train_name="Agra Passenger",
            track_section_id="SEC-01",
            scheduled_arrival=datetime(2026, 10, 15, 13, 0, tzinfo=sample_tz),
            scheduled_departure=datetime(2026, 10, 15, 13, 30, tzinfo=sample_tz),
            train_type="PASSENGER",
            priority_weight=1.0,
        ),
    ]


@pytest.fixture
def sample_traffic_density(sample_tz) -> list[TrafficDensityRecord]:
    return [
        TrafficDensityRecord(
            track_section_id="SEC-01",
            start_time=datetime(2026, 10, 15, 8, 0, tzinfo=sample_tz),
            end_time=datetime(2026, 10, 15, 10, 30, tzinfo=sample_tz),
            density_score=0.85,
            density_category=TrafficDensityCategory.HIGH,
        ),
        TrafficDensityRecord(
            track_section_id="SEC-01",
            start_time=datetime(2026, 10, 15, 10, 30, tzinfo=sample_tz),
            end_time=datetime(2026, 10, 15, 13, 0, tzinfo=sample_tz),
            density_score=0.15,
            density_category=TrafficDensityCategory.LOW,
        ),
        TrafficDensityRecord(
            track_section_id="SEC-01",
            start_time=datetime(2026, 10, 15, 13, 0, tzinfo=sample_tz),
            end_time=datetime(2026, 10, 15, 15, 0, tzinfo=sample_tz),
            density_score=0.60,
            density_category=TrafficDensityCategory.MEDIUM,
        ),
    ]


@pytest.fixture
def sample_resources(sample_tz) -> list[ResourceAvailabilityRecord]:
    return [
        ResourceAvailabilityRecord(
            resource_id="TRACK_TEAM_A",
            resource_name="Permanent Way Team A",
            available_start=datetime(2026, 10, 15, 6, 0, tzinfo=sample_tz),
            available_end=datetime(2026, 10, 15, 18, 0, tzinfo=sample_tz),
            quantity_available=2,
        ),
        ResourceAvailabilityRecord(
            resource_id="TAMPING_MACHINE_01",
            resource_name="CSM Tamping Machine",
            available_start=datetime(2026, 10, 15, 10, 0, tzinfo=sample_tz),
            available_end=datetime(2026, 10, 15, 14, 0, tzinfo=sample_tz),
            quantity_available=1,
        ),
    ]


@pytest.fixture
def sample_sections(sample_tz) -> list[SectionAvailabilityRecord]:
    return [
        SectionAvailabilityRecord(
            track_section_id="SEC-01",
            available_start=datetime(2026, 10, 15, 0, 0, tzinfo=sample_tz),
            available_end=datetime(2026, 10, 16, 0, 0, tzinfo=sample_tz),
            is_blocked=False,
        )
    ]


@pytest.fixture
def baseline_predictor() -> BaselineDelayPredictor:
    return BaselineDelayPredictor()


@pytest.fixture
def mock_validator() -> MockMember4Validator:
    return MockMember4Validator()
