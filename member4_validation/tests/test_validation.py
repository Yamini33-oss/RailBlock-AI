"""
Automated tests for KAVACH BIE Member 4.

Run with:  python -m pytest -v

Every test uses TEMPORARY CSV files (pytest's tmp_path), so the demonstration
CSV files in the project folder are never modified. No internet is needed.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make sure the project folder is importable (main.py and api.py live there).
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import api  # noqa: E402
import main  # noqa: E402

SCHEDULE_HEADER = "train_id,train_name,track_section,start_time,end_time\n"
RESOURCES_TEXT = (
    "resource_name,available\n"
    "Maintenance Team,true\n"
    "Repair Equipment,true\n"
    "Safety Team,true\n"
    "Inspection Team,false\n"
)
# A quiet SEC-01 train far away from the 13:00-14:00 test window.
FAR_AWAY_TRAIN = "T900,Far Away,SEC-01,2026-10-15 20:00,2026-10-15 21:00\n"


# ----------------------------- helpers --------------------------------------

def write_file(folder, name, text):
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def make_paths(folder, schedule_rows, resources_text=RESOURCES_TEXT):
    """Create temporary schedule + resource CSV files and return both paths."""
    schedule = write_file(folder, "train_schedule.csv", SCHEDULE_HEADER + schedule_rows)
    resources = write_file(folder, "resources.csv", resources_text)
    return schedule, resources


def make_request(**changes):
    """A normal request (SEC-01, 13:00-14:00). Pass keyword arguments to change fields."""
    request = {
        "track_section": "SEC-01",
        "start_time": "2026-10-15 13:00",
        "end_time": "2026-10-15 14:00",
        "required_duration_minutes": 60,
        "required_resources": ["Maintenance Team", "Repair Equipment"],
    }
    request.update(changes)
    return request


def run(request, paths):
    schedule, resources = paths
    return main.validate_maintenance(request, schedule, resources)


# ----------------------------- fixtures -------------------------------------

@pytest.fixture
def data_paths(tmp_path):
    """Standard temporary data: SEC-01 has T101 overlapping 13:00-14:00."""
    rows = (
        "T101,Express Alpha,SEC-01,2026-10-15 13:15,2026-10-15 13:45\n"
        "T102,Local Beta,SEC-01,2026-10-15 12:00,2026-10-15 13:00\n"
        "T103,Freight Gamma,SEC-01,2026-10-15 14:00,2026-10-15 14:40\n"
        "T201,Express Echo,SEC-02,2026-10-15 13:10,2026-10-15 13:50\n"
    )
    return make_paths(tmp_path, rows)


@pytest.fixture
def client(data_paths):
    """A test client whose API reads the temporary files."""
    api.app.dependency_overrides[api.get_data_paths] = lambda: data_paths
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


# ----------------------------- core logic tests -----------------------------

def test_01_overlapping_train_gives_conflict(data_paths):
    result = run(make_request(), data_paths)
    assert result["status"] == "CONFLICT"
    assert result["affected_trains"] == ["T101"]
    assert any("T101" in reason for reason in result["reasons"])


def test_02_no_overlap_and_available_resources_gives_valid(data_paths):
    result = run(make_request(start_time="2026-10-15 08:00", end_time="2026-10-15 09:00"), data_paths)
    assert result["status"] == "VALID"
    assert result["reasons"] == []
    assert result["affected_trains"] == []


def test_03_train_on_other_section_is_not_a_conflict(tmp_path):
    rows = FAR_AWAY_TRAIN + "T201,Other Section,SEC-02,2026-10-15 13:00,2026-10-15 14:00\n"
    result = run(make_request(), make_paths(tmp_path, rows))
    assert result["status"] == "VALID"
    assert result["affected_trains"] == []


def test_04_train_ending_exactly_at_maintenance_start_does_not_overlap(tmp_path):
    rows = "T102,Local Beta,SEC-01,2026-10-15 12:00,2026-10-15 13:00\n"
    result = run(make_request(), make_paths(tmp_path, rows))
    assert result["status"] == "VALID"
    assert result["affected_trains"] == []


def test_05_train_starting_exactly_at_maintenance_end_does_not_overlap(tmp_path):
    rows = "T103,Freight Gamma,SEC-01,2026-10-15 14:00,2026-10-15 15:00\n"
    result = run(make_request(), make_paths(tmp_path, rows))
    assert result["status"] == "VALID"
    assert result["affected_trains"] == []


def test_06_insufficient_maintenance_duration(tmp_path):
    paths = make_paths(tmp_path, FAR_AWAY_TRAIN)
    request = make_request(end_time="2026-10-15 13:30", required_duration_minutes=60)
    result = run(request, paths)
    assert result["status"] == "CONFLICT"
    assert result["window_duration_minutes"] == 30
    assert any("30 minutes" in reason and "60 minutes" in reason for reason in result["reasons"])


def test_07_end_time_earlier_than_start_is_rejected(data_paths):
    request = make_request(start_time="2026-10-15 14:00", end_time="2026-10-15 13:00")
    with pytest.raises(main.InvalidRequestError, match="end_time must be later"):
        run(request, data_paths)


def test_08_equal_start_and_end_is_rejected(data_paths):
    request = make_request(start_time="2026-10-15 13:00", end_time="2026-10-15 13:00")
    with pytest.raises(main.InvalidRequestError, match="end_time must be later"):
        run(request, data_paths)


def test_13_unavailable_resource_is_reported(tmp_path):
    paths = make_paths(tmp_path, FAR_AWAY_TRAIN)
    result = run(make_request(required_resources=["Inspection Team"]), paths)
    assert result["status"] == "CONFLICT"
    assert result["resource_results"][0]["status"] == "UNAVAILABLE"
    assert any("Inspection Team" in reason for reason in result["reasons"])


def test_14_missing_resource_is_reported(tmp_path):
    paths = make_paths(tmp_path, FAR_AWAY_TRAIN)
    result = run(make_request(required_resources=["Helicopter"]), paths)
    assert result["status"] == "CONFLICT"
    assert result["resource_results"][0]["status"] == "NOT_FOUND"
    assert any("does not exist" in reason for reason in result["reasons"])


def test_15_invalid_train_timestamps_are_detected(tmp_path):
    rows = (
        FAR_AWAY_TRAIN
        + "T777,Bad Time,SEC-01,not-a-time,2026-10-15 09:00\n"
        + "T778,Backwards,SEC-01,2026-10-15 10:00,2026-10-15 09:00\n"
    )
    result = run(make_request(), make_paths(tmp_path, rows))
    assert result["status"] == "CONFLICT"  # fails closed, never a false VALID
    invalid = result["invalid_schedule_records"]
    assert [record["train_id"] for record in invalid] == ["T777", "T778"]
    assert invalid[0]["line_number"] == 3
    assert any("invalid record" in reason for reason in result["reasons"])


def test_16_missing_train_id_is_detected(tmp_path):
    rows = FAR_AWAY_TRAIN + ",No Id,SEC-01,2026-10-15 09:00,2026-10-15 10:00\n"
    result = run(make_request(), make_paths(tmp_path, rows))
    assert result["status"] == "CONFLICT"
    assert "train_id is empty" in result["invalid_schedule_records"][0]["problems"]


def test_17_missing_required_csv_column_is_detected(tmp_path):
    schedule = write_file(tmp_path, "train_schedule.csv",
                          "train_id,train_name,track_section,start_time\nT1,A,SEC-01,2026-10-15 09:00\n")
    resources = write_file(tmp_path, "resources.csv", RESOURCES_TEXT)
    with pytest.raises(main.DataFileError, match="end_time"):
        main.validate_maintenance(make_request(), schedule, resources)


def test_18_missing_csv_file_gives_clear_error(tmp_path):
    resources = write_file(tmp_path, "resources.csv", RESOURCES_TEXT)
    with pytest.raises(main.DataFileError, match="not found"):
        main.validate_maintenance(make_request(), tmp_path / "nope.csv", resources)


def test_18b_unreadable_csv_gives_clear_error(tmp_path):
    bad = tmp_path / "train_schedule.csv"
    bad.write_bytes(b"\xff\xfe\x00\xd8 not valid utf-8 \xff\xff\n")
    resources = write_file(tmp_path, "resources.csv", RESOURCES_TEXT)
    with pytest.raises(main.DataFileError, match="Could not read"):
        main.validate_maintenance(make_request(), bad, resources)


def test_extra_unknown_track_section_fails_closed(tmp_path):
    result = run(make_request(track_section="SEC-99"), make_paths(tmp_path, FAR_AWAY_TRAIN))
    assert result["status"] == "CONFLICT"
    assert any("SEC-99" in reason for reason in result["reasons"])


def test_extra_invalid_resource_flag_fails_closed(tmp_path):
    resources = "resource_name,available\nMaintenance Team,maybe\nRepair Equipment,true\n"
    paths = make_paths(tmp_path, FAR_AWAY_TRAIN, resources)
    result = run(make_request(), paths)
    assert result["status"] == "CONFLICT"
    assert result["resource_results"][0]["status"] == "INVALID_DATA"
    assert result["invalid_resource_records"][0]["line_number"] == 2


def test_extra_decimal_and_boolean_durations_are_rejected(data_paths):
    for bad_value in (60.5, True, "60", None):
        with pytest.raises(main.InvalidRequestError):
            run(make_request(required_duration_minutes=bad_value), data_paths)


def test_extra_demo_csv_files_are_valid_and_cover_edge_cases():
    """The shipped demo files load cleanly (they are only read, never changed)."""
    rows = main.load_csv_file(main.DEFAULT_SCHEDULE_PATH, main.SCHEDULE_COLUMNS)
    trains, invalid = main.validate_schedule_rows(rows)
    assert invalid == []
    assert len(trains) >= 8
    assert len({train["track_section"] for train in trains}) >= 3
    conflict = main.validate_maintenance(make_request())
    assert conflict["status"] == "CONFLICT" and conflict["affected_trains"] == ["T101"]
    valid = main.validate_maintenance(
        make_request(start_time="2026-10-15 08:00", end_time="2026-10-15 09:00"))
    assert valid["status"] == "VALID"


# ----------------------------- API tests ------------------------------------

def test_19_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK", "module": "KAVACH BIE Member 4 Validation"}


def test_20_validate_endpoint_response_structure(client):
    response = client.post("/validate", json=make_request())
    assert response.status_code == 200  # a business CONFLICT is still HTTP 200
    body = response.json()
    expected_keys = {
        "status", "track_section", "start_time", "end_time",
        "required_duration_minutes", "window_duration_minutes", "affected_trains",
        "reasons", "resource_results", "invalid_schedule_records",
        "invalid_resource_records", "note",
    }
    assert expected_keys <= set(body)
    assert body["status"] == "CONFLICT"
    assert body["affected_trains"] == ["T101"]
    assert body["resource_results"][0]["status"] == "AVAILABLE"


def test_api_valid_request_returns_valid(client):
    response = client.post(
        "/validate", json=make_request(start_time="2026-10-15 08:00", end_time="2026-10-15 09:00"))
    assert response.status_code == 200
    assert response.json()["status"] == "VALID"
    assert response.json()["reasons"] == []


def test_07_08_api_rejects_bad_time_order(client):
    earlier = client.post("/validate", json=make_request(
        start_time="2026-10-15 14:00", end_time="2026-10-15 13:00"))
    equal = client.post("/validate", json=make_request(
        start_time="2026-10-15 13:00", end_time="2026-10-15 13:00"))
    assert earlier.status_code == 422 and equal.status_code == 422
    assert "later than start_time" in earlier.json()["errors"][0]["message"]


def test_09_api_rejects_missing_track_section(client):
    request = make_request()
    del request["track_section"]
    response = client.post("/validate", json=request)
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "track_section"


def test_10_api_rejects_empty_track_section(client):
    for empty in ("", "   "):
        response = client.post("/validate", json=make_request(track_section=empty))
        assert response.status_code == 422


def test_11_api_rejects_zero_duration(client):
    assert client.post("/validate", json=make_request(required_duration_minutes=0)).status_code == 422


def test_12_api_rejects_negative_duration(client):
    assert client.post("/validate", json=make_request(required_duration_minutes=-5)).status_code == 422


def test_api_rejects_decimal_boolean_and_malformed_values(client):
    for changes in (
        {"required_duration_minutes": 60.5},
        {"required_duration_minutes": True},
        {"start_time": "15/10/2026 13:00"},
        {"end_time": "tomorrow"},
        {"start_time": "2026-02-30 13:00"},
        {"required_resources": "Maintenance Team"},
    ):
        response = client.post("/validate", json=make_request(**changes))
        assert response.status_code == 422, changes
        assert response.json()["status"] == "INVALID_REQUEST"


def test_api_rejects_malformed_json_body(client):
    response = client.post("/validate", content="{not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_18_api_reports_missing_csv_file_as_server_error(tmp_path):
    missing = tmp_path / "missing.csv"
    resources = write_file(tmp_path, "resources.csv", RESOURCES_TEXT)
    api.app.dependency_overrides[api.get_data_paths] = lambda: (missing, resources)
    try:
        response = TestClient(api.app).post("/validate", json=make_request())
    finally:
        api.app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json()["status"] == "DATA_FILE_ERROR"
    assert "not found" in response.json()["detail"]
