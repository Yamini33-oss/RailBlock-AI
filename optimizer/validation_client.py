"""Conflict validation client and adapter for Member 4 integration.

Connects to Member 4's operational validation engine to verify candidate blocks
against live headway, signaling, station interlocking, and operational rules.
Provides a clearly labeled mock validator for testing and development.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import requests

from optimizer.exceptions import ValidationServiceError
from optimizer.schemas import (
    CandidateEvaluation,
    ValidationRequest,
    ValidationResult,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


class ConflictValidationInterface(ABC):
    """Abstract interface for Member 4 operational conflict validation."""

    @abstractmethod
    def validate_candidate(
        self,
        candidate_eval: CandidateEvaluation,
    ) -> ValidationResult:
        """Validate a proposed maintenance block candidate against operational constraints."""
        pass


class MockMember4Validator(ConflictValidationInterface):
    """Explicitly labeled test double for Member 4 conflict validation.

    WARNING: This is a synthetic mock validator for development and testing only.
    It does NOT provide official railway safety certification or live operational validation.
    """

    def __init__(
        self,
        max_allowed_affected_trains: int = 10,
        rejected_candidate_ids: Optional[List[str]] = None,
        simulate_unavailable: bool = False,
        simulate_error: bool = False,
        custom_rule_fn: Optional[Callable[[CandidateEvaluation], ValidationResult]] = None,
    ) -> None:
        self.max_allowed_affected_trains = max_allowed_affected_trains
        self.rejected_candidate_ids = set(rejected_candidate_ids or [])
        self.simulate_unavailable = simulate_unavailable
        self.simulate_error = simulate_error
        self.custom_rule_fn = custom_rule_fn
        self.validation_calls: List[str] = []

    def validate_candidate(
        self,
        candidate_eval: CandidateEvaluation,
    ) -> ValidationResult:
        self.validation_calls.append(candidate_eval.candidate_id)

        if self.simulate_unavailable:
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.VALIDATION_UNAVAILABLE,
                reason="Member 4 conflict detection service is currently unreachable.",
                validator_name="MockMember4Validator (Simulated Unavailable)",
            )

        if self.simulate_error:
            raise ValidationServiceError(
                "Member 4 validation service raised an internal communication error.",
                details={"candidate_id": candidate_eval.candidate_id},
            )

        if self.custom_rule_fn is not None:
            return self.custom_rule_fn(candidate_eval)

        # Check explicit reject list
        if candidate_eval.candidate_id in self.rejected_candidate_ids:
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.CONFLICT,
                reason=f"Operational conflict on section {candidate_eval.track_section_id}: Candidate {candidate_eval.candidate_id} rejected by rule.",
                conflict_details=[f"Simulated conflict for {candidate_eval.candidate_id}"],
                validator_name="MockMember4Validator",
            )

        # Check affected train threshold
        if candidate_eval.affected_train_count > self.max_allowed_affected_trains:
            conflicting_trains = candidate_eval.affected_trains
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.CONFLICT,
                reason=(
                    f"Operational conflict: {candidate_eval.affected_train_count} affected trains "
                    f"exceeds maximum allowed threshold ({self.max_allowed_affected_trains})."
                ),
                conflict_details=conflicting_trains,
                validator_name="MockMember4Validator",
            )

        return ValidationResult(
            candidate_id=candidate_eval.candidate_id,
            status=ValidationStatus.VALID,
            reason="No operational headway or interlocking conflicts detected by Member 4 validator.",
            validator_name="MockMember4Validator",
        )


class Member4HTTPClient(ConflictValidationInterface):
    """Production HTTP client to communicate with Member 4's FastAPI validation microservice."""

    def __init__(
        self,
        base_url: str = "http://localhost:8004",
        endpoint: str = "/api/validation/validate",
        timeout_seconds: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def validate_candidate(
        self,
        candidate_eval: CandidateEvaluation,
    ) -> ValidationResult:
        url = f"{self.base_url}{self.endpoint}"
        payload = {
            "candidate_id": candidate_eval.candidate_id,
            "track_section_id": candidate_eval.track_section_id,
            "start_time": candidate_eval.start_time.isoformat(),
            "end_time": candidate_eval.end_time.isoformat(),
            "duration_minutes": candidate_eval.duration_minutes,
            "affected_trains": candidate_eval.affected_trains,
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                status_str = data.get("status", "VALID")
                return ValidationResult(
                    candidate_id=candidate_eval.candidate_id,
                    status=ValidationStatus(status_str),
                    reason=data.get("reason"),
                    conflict_details=data.get("conflict_details"),
                    validator_name=data.get("validator_name", "Member4HTTPService"),
                )
            else:
                logger.error("Member 4 service returned HTTP %d: %s", resp.status_code, resp.text)
                return ValidationResult(
                    candidate_id=candidate_eval.candidate_id,
                    status=ValidationStatus.VALIDATION_ERROR,
                    reason=f"Member 4 validation service HTTP error {resp.status_code}: {resp.text}",
                    validator_name="Member4HTTPService",
                )
        except requests.exceptions.RequestException as exc:
            logger.warning("Could not reach Member 4 validation service at %s: %s", url, exc)
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.VALIDATION_UNAVAILABLE,
                reason=f"Member 4 validation service unavailable: {exc}",
                validator_name="Member4HTTPService",
            )
