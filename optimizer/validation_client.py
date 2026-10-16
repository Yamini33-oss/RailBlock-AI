
"""Conflict validation client and adapter for Member 4 integration."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional

import requests

from optimizer.exceptions import ValidationServiceError
from optimizer.schemas import (
    CandidateEvaluation,
    ValidationResult,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


class ConflictValidationInterface(ABC):
    """Interface for Member 4 conflict validation."""

    @abstractmethod
    def validate_candidate(
        self, candidate_eval: CandidateEvaluation
    ) -> ValidationResult:
        """Validate a proposed maintenance window."""
        pass


class MockMember4Validator(ConflictValidationInterface):
    """Test-only mock validator."""

    def __init__(
        self,
        max_allowed_affected_trains: int = 10,
        rejected_candidate_ids: Optional[List[str]] = None,
        simulate_unavailable: bool = False,
        simulate_error: bool = False,
        custom_rule_fn: Optional[
            Callable[[CandidateEvaluation], ValidationResult]
        ] = None,
    ) -> None:
        self.max_allowed_affected_trains = max_allowed_affected_trains
        self.rejected_candidate_ids = set(rejected_candidate_ids or [])
        self.simulate_unavailable = simulate_unavailable
        self.simulate_error = simulate_error
        self.custom_rule_fn = custom_rule_fn
        self.validation_calls: List[str] = []

    def validate_candidate(
        self, candidate_eval: CandidateEvaluation
    ) -> ValidationResult:
        self.validation_calls.append(candidate_eval.candidate_id)

        if self.simulate_unavailable:
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.VALIDATION_UNAVAILABLE,
                reason="Member 4 validation service is unreachable.",
                validator_name="MockMember4Validator",
            )

        if self.simulate_error:
            raise ValidationServiceError(
                "Simulated Member 4 communication error.",
                details={"candidate_id": candidate_eval.candidate_id},
            )

        if self.custom_rule_fn is not None:
            return self.custom_rule_fn(candidate_eval)

        if candidate_eval.candidate_id in self.rejected_candidate_ids:
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.CONFLICT,
                reason="Candidate rejected by the mock validation rule.",
                conflict_details=[
                    f"Simulated conflict for {candidate_eval.candidate_id}"
                ],
                validator_name="MockMember4Validator",
            )

        if (
            candidate_eval.affected_train_count
            > self.max_allowed_affected_trains
        ):
            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.CONFLICT,
                reason=(
                    "Affected train count exceeds the mock validator's "
                    f"limit of {self.max_allowed_affected_trains}."
                ),
                conflict_details=candidate_eval.affected_trains,
                validator_name="MockMember4Validator",
            )

        return ValidationResult(
            candidate_id=candidate_eval.candidate_id,
            status=ValidationStatus.VALID,
            reason="Passed mock validation only.",
            validator_name="MockMember4Validator",
        )


class Member4HTTPClient(ConflictValidationInterface):
    """HTTP client for Member 4's FastAPI validation service."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8004",
        endpoint: str = "/validate",
        timeout_seconds: float = 5.0,
        required_resources: Optional[List[str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = "/" + endpoint.lstrip("/")
        self.timeout_seconds = timeout_seconds
        self.required_resources = (
            required_resources
            if required_resources is not None
            else ["Maintenance Team"]
        )

    def validate_candidate(
        self, candidate_eval: CandidateEvaluation
    ) -> ValidationResult:
        url = f"{self.base_url}{self.endpoint}"

        payload = {
            "track_section": candidate_eval.track_section_id,
            "start_time": candidate_eval.start_time.strftime(
                "%Y-%m-%d %H:%M"
            ),
            "end_time": candidate_eval.end_time.strftime(
                "%Y-%m-%d %H:%M"
            ),
            "required_duration_minutes": candidate_eval.duration_minutes,
            "required_resources": self.required_resources,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=self.timeout_seconds,
            )

            try:
                data: Any = response.json()
            except ValueError:
                data = {"message": response.text}

            if response.status_code == 200:
                if isinstance(data, dict):
                    status_value = str(data.get("status", "")).upper()

                    raw_reasons = data.get("reasons", [])
                    if isinstance(raw_reasons, list):
                        reasons = raw_reasons
                    elif raw_reasons:
                        reasons = [str(raw_reasons)]
                    else:
                        reasons = []

                    reason = (
                        data.get("reason")
                        or "; ".join(str(item) for item in reasons)
                        or data.get("message")
                        or "Member 4 returned a response."
                    )

                    conflict_details = (
                        data.get("conflict_details") or reasons or None
                    )

                    validator_name = data.get(
                        "validator_name", "Member4HTTPService"
                    )
                else:
                    status_value = ""
                    reason = str(data)
                    conflict_details = None
                    validator_name = "Member4HTTPService"

                # Do not silently accept an unknown or missing status.
                try:
                    validation_status = ValidationStatus(status_value)
                except ValueError:
                    validation_status = ValidationStatus.VALIDATION_ERROR
                    reason = (
                        f"Unrecognized or missing Member 4 status "
                        f"'{status_value}'. Response: {reason}"
                    )

                return ValidationResult(
                    candidate_id=candidate_eval.candidate_id,
                    status=validation_status,
                    reason=str(reason),
                    conflict_details=conflict_details,
                    validator_name=validator_name,
                )

            logger.error(
                "Member 4 returned HTTP %s: %s",
                response.status_code,
                response.text,
            )

            errors = (
                data.get("errors", data.get("detail", data))
                if isinstance(data, dict)
                else data
            )

            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.VALIDATION_ERROR,
                reason=(
                    f"Member 4 returned HTTP {response.status_code}: "
                    f"{errors}"
                ),
                validator_name="Member4HTTPService",
            )

        except requests.exceptions.RequestException as exc:
            logger.warning(
                "Member 4 is unreachable at %s: %s", url, exc
            )

            return ValidationResult(
                candidate_id=candidate_eval.candidate_id,
                status=ValidationStatus.VALIDATION_UNAVAILABLE,
                reason=f"Member 4 validation service unavailable: {exc}",
                validator_name="Member4HTTPService",
            )
