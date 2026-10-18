"""Real integration tests for Member 2 delay prediction and Member 4 conflict validation.

Tests both modules using their real models, real APIs, and synthetic data,
verifying all 8 mandatory audit scenarios from the problem specification:
1. Valid maintenance window.
2. Window overlapping scheduled train movements.
3. Unavailable resource.
4. Blocked track section.
5. Duration or planning boundary violations.
6. Service timeout / unavailable validation service.
7. Scenario where no feasible block exists.
8. Complete request-to-recommendation workflow through the API contract.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient

from KAVACH_BIE_MEMBER2.api import app as member2_app
from member4_validation.api import app as member4_app
from optimizer.api import app as optimizer_app
from optimizer.data_adapter import (
    DataLoader,
    Member2PredictorAdapter,
)
from optimizer.schemas import (
    CandidateEvaluation,
    MaintenancePriority,
    MaintenanceRequest,
    OptimizationStatus,
    PlanningConfig,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    ValidationResult,
    ValidationStatus,
)
from optimizer.service import optimize_maintenance_window
from optimizer.validation_client import Member4HTTPClient, MockMember4Validator

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Test Member 4 API Directly
# ---------------------------------------------------------------------------

def test_member4_live_health():
    """Verify Member 4 /health returns OK."""
    client = TestClient(member4_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "OK"


def test_member4_live_valid_window():
    """Verify Member 4 validates a clear window with available resources."""
    client = TestClient(member4_app)
    payload = {
        "track_section": "SEC-01",
        "start_time": "2026-10-15 10:30",
        "end_time": "2026-10-15 11:30",
        "required_duration_minutes": 60,
        "required_resources": ["Maintenance Team"],
    }
    resp = client.post("/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "VALID"
    assert data["affected_trains"] == []
    assert data["reasons"] == []


def test_member4_live_train_conflict():
    """Verify Member 4 detects a conflict with scheduled train T102."""
    client = TestClient(member4_app)
    payload = {
        "track_section": "SEC-01",
        "start_time": "2026-10-15 12:00",
        "end_time": "2026-10-15 13:00",
        "required_duration_minutes": 60,
        "required_resources": ["Maintenance Team"],
    }
    resp = client.post("/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CONFLICT"
    assert "T102" in data["affected_trains"]
    assert any("T102" in r for r in data["reasons"])


def test_member4_live_unavailable_resource():
    """Verify Member 4 detects an unavailable resource (Inspection Team)."""
    client = TestClient(member4_app)
    payload = {
        "track_section": "SEC-01",
        "start_time": "2026-10-15 10:30",
        "end_time": "2026-10-15 11:30",
        "required_duration_minutes": 60,
        "required_resources": ["Inspection Team"],
    }
    resp = client.post("/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CONFLICT"
    assert any("Inspection Team" in r for r in data["reasons"])


def test_member4_live_malformed_request_422():
    """Verify Member 4 returns 422 for malformed requests."""
    client = TestClient(member4_app)
    payload = {
        "track_section": "",
        "start_time": "invalid",
        "end_time": "2026-10-15 11:30",
        "required_duration_minutes": -5,
    }
    resp = client.post("/validate", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["status"] == "INVALID_REQUEST"
    assert len(data["errors"]) >= 1


# ---------------------------------------------------------------------------
# Test Member 2 API Directly
# ---------------------------------------------------------------------------

def test_member2_live_health():
    """Verify Member 2 /health returns healthy and model loaded."""
    client = TestClient(member2_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True


def test_member2_live_prediction():
    """Verify Member 2 predicts delay and disruption for a candidate window."""
    client = TestClient(member2_app)
    payload = {
        "request_id": "REQ-TEST-M2",
        "track_section": "SEC-01",
        "requested_date": "2026-10-15",
        "proposed_start_time": "10:30",
        "proposed_end_time": "11:30",
        "required_duration_minutes": 60,
        "maintenance_priority": "HIGH",
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_delay_minutes" in data
    assert data["predicted_delay_minutes"] >= 0.0
    assert "disruption_score" in data
    assert data["risk_category"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ---------------------------------------------------------------------------
# Test Member 4 Adapter Integration in Optimizer
# ---------------------------------------------------------------------------

class TestClientMember4Validator(Member4HTTPClient):
    """Adapter that routes HTTP requests to member4 FastAPI TestClient directly."""
    __test__ = False

    def __init__(self, required_resources=None):
        super().__init__(
            base_url="http://testserver",
            endpoint="/validate",
            required_resources=required_resources or ["Maintenance Team"],
        )
        self.client = TestClient(member4_app)

    def validate_candidate(self, candidate_eval: CandidateEvaluation) -> ValidationResult:
        payload = {
            "track_section": candidate_eval.track_section_id,
            "start_time": candidate_eval.start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": candidate_eval.end_time.strftime("%Y-%m-%d %H:%M"),
            "required_duration_minutes": candidate_eval.duration_minutes,
            "required_resources": self.required_resources,
        }
        resp = self.client.post("/validate", json=payload)
        data = resp.json()

        if resp.status_code == 200:
            status_val = ValidationStatus(str(data.get("status", "")).upper())
            reasons = data.get("reasons", [])
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=status_val,
                reason="; ".join(reasons) if reasons else "Passed Member 4 conflict validation.",
                conflict_details=data.get("affected_trains") or reasons or None,
                validator_name="Member4HTTPService",
            )
        return ValidationResult(
            candidate_id=candidate_eval.candidate_id,
            status=ValidationStatus.VALIDATION_ERROR,
            reason=f"HTTP {resp.status_code}: {data}",
            validator_name="Member4HTTPService",
        )


class TestClientMember2Predictor:
    """Predictor that routes calls to Member 2's live trained ML model."""
    __test__ = False

    def __init__(self):
        from KAVACH_BIE_MEMBER2.predict_delay import predict_maintenance_window
        from KAVACH_BIE_MEMBER2.prediction_schema import MaintenanceWindowRequest
        self._predict = predict_maintenance_window
        self._schema = MaintenanceWindowRequest

    def __call__(self, candidate_window, train_data, traffic_data):
        st = candidate_window.start_time
        et = candidate_window.end_time
        req = self._schema(
            request_id=candidate_window.candidate_id,
            track_section=candidate_window.track_section_id,
            requested_date=st.strftime("%Y-%m-%d"),
            proposed_start_time=st.strftime("%H:%M"),
            proposed_end_time=et.strftime("%H:%M"),
            required_duration_minutes=candidate_window.duration_minutes,
            maintenance_priority="MEDIUM",
        )
        return self._predict(req)


# ---------------------------------------------------------------------------
# 8 Mandatory Scenario Verifications
# ---------------------------------------------------------------------------

def test_mandatory_scenario_1_valid_maintenance_window():
    """Scenario 1: A valid maintenance window with real Member 4 validation."""
    m2_adapter = Member2PredictorAdapter(
        predictor_callable=TestClientMember2Predictor(),
        fallback_to_baseline=True,
    )
    m4_validator = TestClientMember4Validator(required_resources=["Maintenance Team"])

    req = MaintenanceRequest(
        request_id="REQ-SCENARIO-1",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=[],  # Handled by validator default
    )
    resp = optimize_maintenance_window(
        request=req,
        predictor=m2_adapter,
        validator=m4_validator,
        config=PlanningConfig(step_minutes=30),
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    assert resp.recommendation is not None
    assert resp.validation is not None
    assert resp.validation.status == ValidationStatus.VALID
    assert resp.validation.validator_used == "Member4HTTPService"


def test_mandatory_scenario_2_overlapping_train_movements(sample_train_schedules):
    """Scenario 2: Candidate window overlapping scheduled trains is rejected or penalized."""
    # Scheduled train on SEC-01 at 09:10-09:40
    req = MaintenanceRequest(
        request_id="REQ-SCENARIO-2",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 9, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
    )
    resp = optimize_maintenance_window(
        request=req,
        input_data={"train_data": sample_train_schedules},
        config=PlanningConfig(step_minutes=30),
    )

    assert resp.status == OptimizationStatus.RECOMMENDED
    # The recommended window must NOT be 09:00-10:00 (which has train overlap)
    assert resp.recommendation.start_time >= datetime(2026, 10, 15, 10, 0, tzinfo=IST)


def test_mandatory_scenario_3_unavailable_resource():
    """Scenario 3: An unavailable resource causes candidate rejection."""
    res_record = ResourceAvailabilityRecord(
        resource_id="SPECIAL_CRANE",
        resource_name="Heavy Crane",
        available_start=datetime(2026, 10, 15, 16, 0, tzinfo=IST),
        available_end=datetime(2026, 10, 15, 18, 0, tzinfo=IST),
        quantity_available=1,
    )
    # Request planning horizon 10:00 to 14:00 (resource only available after 16:00)
    req = MaintenanceRequest(
        request_id="REQ-SCENARIO-3",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 14, 0, tzinfo=IST),
        required_duration_minutes=60,
        required_resources=["SPECIAL_CRANE"],
    )
    resp = optimize_maintenance_window(
        request=req,
        input_data={"resource_data": [res_record]},
    )

    assert resp.status == OptimizationStatus.NO_FEASIBLE_WINDOW
    assert resp.recommendation is None
    assert len(resp.rejected_candidates) > 0
    assert any("unavailable" in r.lower() for r in resp.rejected_candidates[0].reasons)


def test_mandatory_scenario_4_blocked_track_section():
    """Scenario 4: A section that is blocked is rejected by the candidate evaluator."""
    blocked_section = SectionAvailabilityRecord(
        track_section_id="SEC-01",
        available_start=datetime(2026, 10, 15, 9, 0, tzinfo=IST),
        available_end=datetime(2026, 10, 15, 15, 0, tzinfo=IST),
        is_blocked=True,
        block_reason="Emergency Track Repair Outage",
    )
    req = MaintenanceRequest(
        request_id="REQ-SCENARIO-4",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
    )
    resp = optimize_maintenance_window(
        request=req,
        input_data={"section_data": [blocked_section]},
    )

    assert resp.status == OptimizationStatus.NO_FEASIBLE_WINDOW
    assert resp.recommendation is None
    assert len(resp.rejected_candidates) > 0
    assert any("Emergency Track Repair Outage" in r for r in resp.rejected_candidates[0].reasons)


def test_mandatory_scenario_5_duration_boundary_violation():
    """Scenario 5: Request violating duration or horizon boundaries is rejected as INVALID_REQUEST."""
    # Required duration (180m) exceeds planning horizon (10:00 to 11:00 = 60m)
    invalid_dict = {
        "request_id": "REQ-SCENARIO-5",
        "track_section_id": "SEC-01",
        "planning_start": "2026-10-15T10:00:00+05:30",
        "planning_end": "2026-10-15T11:00:00+05:30",
        "required_duration_minutes": 180,
    }
    resp = optimize_maintenance_window(request=invalid_dict)
    assert resp.status == OptimizationStatus.INVALID_REQUEST
    assert resp.recommendation is None


def test_mandatory_scenario_6_validation_service_unavailable():
    """Scenario 6: Validation service timeout/unreachable returns VALIDATION_UNAVAILABLE, never false VALID."""
    # Point client to non-existent port to simulate unreachable service
    unreachable_client = Member4HTTPClient(base_url="http://127.0.0.1:59999", timeout_seconds=0.5)

    req = MaintenanceRequest(
        request_id="REQ-SCENARIO-6",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
    )
    resp = optimize_maintenance_window(
        request=req,
        validator=unreachable_client,
        config=PlanningConfig(allow_unvalidated_fallback=False),
    )

    assert resp.status == OptimizationStatus.VALIDATION_UNAVAILABLE
    assert resp.recommendation is None
    assert "unavailable" in " ".join(resp.explanation).lower()


def test_mandatory_scenario_7_no_feasible_window_exists():
    """Scenario 7: When every candidate window conflicts, returns NO_FEASIBLE_WINDOW."""
    reject_all_validator = MockMember4Validator(
        custom_rule_fn=lambda cand: ValidationResult(
            candidate_id=cand.candidate_id,
            status=ValidationStatus.CONFLICT,
            reason="All windows blocked by major corridor overhaul",
            validator_name="MockMember4Validator",
        )
    )
    req = MaintenanceRequest(
        request_id="REQ-SCENARIO-7",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 12, 0, tzinfo=IST),
        required_duration_minutes=60,
    )
    resp = optimize_maintenance_window(
        request=req,
        validator=reject_all_validator,
    )

    assert resp.status == OptimizationStatus.NO_FEASIBLE_WINDOW
    assert resp.recommendation is None
    assert len(resp.rejected_candidates) > 0


def test_mandatory_scenario_8_complete_workflow_via_api():
    """Scenario 8: Complete request-to-recommendation workflow via the API router."""
    client = TestClient(optimizer_app)
    payload = {
        "request_id": "REQ-SCENARIO-8",
        "track_section_id": "SEC-01",
        "planning_start": "2026-10-15T09:00:00+05:30",
        "planning_end": "2026-10-15T18:00:00+05:30",
        "required_duration_minutes": 60,
        "maintenance_priority": "MEDIUM",
        "earliest_start_time": "2026-10-15T10:00:00+05:30",
        "latest_end_time": "2026-10-15T17:00:00+05:30",
        "use_real_validator": False,
        "use_real_predictor": True,  # Uses real Member 2 ML model
    }
    resp = client.post("/api/optimization/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "RECOMMENDED"
    assert data["recommendation"] is not None
    assert data["recommendation"]["track_section_id"] == "SEC-01"
    assert data["recommendation"]["duration_minutes"] == 60
    assert data["estimated_impact"] is not None
    assert len(data["alternatives"]) >= 1
    assert len(data["explanation"]) >= 1
