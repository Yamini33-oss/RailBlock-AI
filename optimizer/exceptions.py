"""Custom domain exceptions for KAVACH BIE Member 3 Optimization Engine."""

from typing import Any, Dict, Optional


class OptimizerBaseException(Exception):
    """Base exception for all optimizer domain errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "OPTIMIZATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class InvalidRequestError(OptimizerBaseException):
    """Raised when a maintenance request violates validation rules."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="INVALID_REQUEST", details=details)


class DataValidationError(OptimizerBaseException):
    """Raised when input datasets (schedules, traffic, resources) fail validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="DATA_VALIDATION_ERROR", details=details)


class NoFeasibleWindowError(OptimizerBaseException):
    """Raised when no candidate window satisfies hard constraints and operational validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="NO_FEASIBLE_WINDOW", details=details)


class PredictionServiceError(OptimizerBaseException):
    """Raised when Member 2 delay prediction service fails or is unreachable."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="PREDICTION_UNAVAILABLE", details=details)


class ValidationServiceError(OptimizerBaseException):
    """Raised when Member 4 conflict validation service fails or is unreachable."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class SolverError(OptimizerBaseException):
    """Raised when the OR-Tools CP-SAT solver encounters an internal or timeout error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="SOLVER_ERROR", details=details)


class DependencyMissingError(OptimizerBaseException):
    """Raised when an essential dependency (e.g. ortools) is missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="DEPENDENCY_MISSING", details=details)
