"""Tests for Member 4 conflict validation client and adapters."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from optimizer.exceptions import ValidationServiceError
from optimizer.schemas import CandidateEvaluation, ValidationStatus
from optimizer.validation_client import MockMember4Validator

IST = ZoneInfo("Asia/Kolkata")


def make_eval(cand_id: str, affected_trains: int) -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate_id=cand_id,
        track_section_id="SEC-01",
        start_time=datetime(2026, 10, 15, 10, 0, tzinfo=IST),
        end_time=datetime(2026, 10, 15, 11, 0, tzinfo=IST),
        duration_minutes=60,
        affected_train_count=affected_trains,
        affected_trains=[f"TR-{i}" for i in range(affected_trains)],
    )


def test_validator_approves_normal_candidate():
    validator = MockMember4Validator(max_allowed_affected_trains=5)
    ev = make_eval("CW-01", affected_trains=2)
    res = validator.validate_candidate(ev)

    assert res.status == ValidationStatus.VALID
    assert res.candidate_id == "CW-01"


def test_validator_rejects_excess_affected_trains():
    validator = MockMember4Validator(max_allowed_affected_trains=2)
    ev = make_eval("CW-BUSY", affected_trains=4)
    res = validator.validate_candidate(ev)

    assert res.status == ValidationStatus.CONFLICT
    assert "exceeds maximum allowed threshold" in res.reason


def test_validator_rejects_specific_candidate_id():
    validator = MockMember4Validator(rejected_candidate_ids=["CW-CONFLICT-01"])
    ev = make_eval("CW-CONFLICT-01", affected_trains=0)
    res = validator.validate_candidate(ev)

    assert res.status == ValidationStatus.CONFLICT
    assert "CW-CONFLICT-01 rejected" in res.reason


def test_validator_simulates_service_unavailable():
    validator = MockMember4Validator(simulate_unavailable=True)
    ev = make_eval("CW-01", affected_trains=0)
    res = validator.validate_candidate(ev)

    assert res.status == ValidationStatus.VALIDATION_UNAVAILABLE
    assert "unreachable" in res.reason


def test_validator_simulates_service_error():
    validator = MockMember4Validator(simulate_error=True)
    ev = make_eval("CW-01", affected_trains=0)
    with pytest.raises(ValidationServiceError):
        validator.validate_candidate(ev)
