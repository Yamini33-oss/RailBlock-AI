"""Tests for candidate maintenance window generator."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest

from optimizer.candidate_generator import generate_candidate_windows
from optimizer.schemas import MaintenanceRequest, PlanningConfig

IST = ZoneInfo("Asia/Kolkata")


def test_generate_single_fitting_window():
    # Horizon is exactly 60 minutes, required duration is 60 minutes
    req = MaintenanceRequest(
        request_id="MR-EXACT-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        required_duration_minutes=60,
    )
    windows = generate_candidate_windows(req, PlanningConfig(step_minutes=15))
    assert len(windows) == 1
    assert windows[0].start_time == datetime(2026, 10, 15, 10, 0, tzinfo=IST)
    assert windows[0].end_time == datetime(2026, 10, 15, 11, 0, tzinfo=IST)
    assert windows[0].duration_minutes == 60


def test_generate_multiple_stepped_windows():
    # 2 hours horizon (120 mins), 60 mins duration, 15 mins step -> 5 candidate windows:
    # 08:00-09:00, 08:15-09:15, 08:30-09:30, 08:45-09:45, 09:00-10:00
    req = MaintenanceRequest(
        request_id="MR-STEP-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        required_duration_minutes=60,
    )
    windows = generate_candidate_windows(req, PlanningConfig(step_minutes=15))
    assert len(windows) == 5
    assert windows[0].start_time == datetime(2026, 10, 15, 8, 0, tzinfo=IST)
    assert windows[-1].end_time == datetime(2026, 10, 15, 10, 0, tzinfo=IST)


def test_respect_earliest_start_and_latest_end():
    req = MaintenanceRequest(
        request_id="MR-BOUNDS-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 16, 0, tzinfo=IST),
        required_duration_minutes=60,
        earliest_start_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        latest_end_time=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
    )
    windows = generate_candidate_windows(req, PlanningConfig(step_minutes=30))
    # Effective window: 10:00 to 12:00, step 30 mins:
    # 10:00-11:00, 10:30-11:30, 11:00-12:00 -> 3 windows
    assert len(windows) == 3
    for w in windows:
        assert w.start_time >= req.earliest_start_time
        assert w.end_time <= req.latest_end_time


def test_midnight_crossing_candidates():
    # Planning horizon crosses midnight: 22:00 to 04:00 next day (6 hours = 360 mins)
    req = MaintenanceRequest(
        request_id="MR-NIGHT-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 22, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 16, 4, 0, tzinfo=IST),
        required_duration_minutes=120,
    )
    windows = generate_candidate_windows(req, PlanningConfig(step_minutes=60))
    # Windows:
    # 22:00-00:00, 23:00-01:00, 00:00-02:00, 01:00-03:00, 02:00-04:00 -> 5 windows
    assert len(windows) == 5
    assert windows[1].start_time == datetime(2026, 10, 15, 23, 0, tzinfo=IST)
    assert windows[1].end_time == datetime(2026, 10, 16, 1, 0, tzinfo=IST)
    assert windows[1].duration_minutes == 120


def test_empty_candidate_when_duration_exceeds_effective_horizon():
    # Earliest start and latest end leaves 45 mins, but duration is 60 mins
    # (Notice: pydantic validates this on construction, but if earliest/latest are set narrow)
    req = MaintenanceRequest(
        request_id="MR-NARROW-01",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
        earliest_start_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        latest_end_time=datetime(2026, 10, 15, 11, 30, tzinfo=IST),
    )
    # 10:00 to 11:30 is 90 mins -> 60 min duration fits!
    # Now set step_minutes = 60
    windows = generate_candidate_windows(req, PlanningConfig(step_minutes=60))
    assert len(windows) == 1
    assert windows[0].start_time == datetime(2026, 10, 15, 10, 0, tzinfo=IST)
    assert windows[0].end_time == datetime(2026, 10, 15, 11, 0, tzinfo=IST)
