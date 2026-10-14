"""Pydantic schemas and data contracts for KAVACH BIE Member 3 Optimization Engine.

Defines all input, internal evaluation, configuration, and output models.
Strictly compatible with Pydantic v2 and FastAPI serialization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MaintenancePriority(str, Enum):
    """Priority level for railway maintenance requests."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class OptimizationStatus(str, Enum):
    """Overall status of the optimization and validation process."""
    RECOMMENDED = "RECOMMENDED"
    NO_FEASIBLE_WINDOW = "NO_FEASIBLE_WINDOW"
    INVALID_REQUEST = "INVALID_REQUEST"
    PREDICTION_UNAVAILABLE = "PREDICTION_UNAVAILABLE"
    VALIDATION_UNAVAILABLE = "VALIDATION_UNAVAILABLE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    OPTIMIZATION_ERROR = "OPTIMIZATION_ERROR"


class SolverStatus(str, Enum):
    """Google OR-Tools CP-SAT solver termination status."""
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    MODEL_INVALID = "MODEL_INVALID"
    TIMEOUT = "TIMEOUT"
    NOT_SOLVED = "NOT_SOLVED"


class ValidationStatus(str, Enum):
    """Operational validation status returned by Member 4."""
    VALID = "VALID"
    CONFLICT = "CONFLICT"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    VALIDATION_UNAVAILABLE = "VALIDATION_UNAVAILABLE"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class TrafficDensityCategory(str, Enum):
    """Traffic density classification for track sections."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ---------------------------------------------------------------------------
# Configuration Models
# ---------------------------------------------------------------------------

class ObjectiveWeights(BaseModel):
    """Configurable weights for multi-objective candidate scoring.
    
    Weights are normalized internally so they sum to 1.0.
    """
    weight_delay: float = Field(default=0.40, ge=0.0, description="Weight for predicted train delay")
    weight_trains: float = Field(default=0.30, ge=0.0, description="Weight for number of affected trains")
    weight_traffic_density: float = Field(default=0.15, ge=0.0, description="Weight for section traffic density")
    weight_slack_duration: float = Field(default=0.05, ge=0.0, description="Weight for excess duration over required")
    weight_priority_urgency: float = Field(default=0.10, ge=0.0, description="Weight for scheduling urgency based on priority")

    def normalized(self) -> Dict[str, float]:
        total = (
            self.weight_delay
            + self.weight_trains
            + self.weight_traffic_density
            + self.weight_slack_duration
            + self.weight_priority_urgency
        )
        if total <= 0:
            return {
                "weight_delay": 0.40,
                "weight_trains": 0.30,
                "weight_traffic_density": 0.15,
                "weight_slack_duration": 0.05,
                "weight_priority_urgency": 0.10,
            }
        return {
            "weight_delay": self.weight_delay / total,
            "weight_trains": self.weight_trains / total,
            "weight_traffic_density": self.weight_traffic_density / total,
            "weight_slack_duration": self.weight_slack_duration / total,
            "weight_priority_urgency": self.weight_priority_urgency / total,
        }


class PlanningConfig(BaseModel):
    """Runtime configuration for candidate generation and solver behavior."""
    step_minutes: int = Field(default=15, gt=0, description="Interval in minutes to shift candidate start times")
    max_validation_attempts: int = Field(default=5, ge=1, description="Max candidate alternatives to test with Member 4")
    solver_time_limit_seconds: float = Field(default=10.0, gt=0.0, description="Time limit for OR-Tools CP-SAT solver")
    max_alternatives: int = Field(default=5, ge=0, description="Maximum number of ranked alternative windows to return")
    weights: ObjectiveWeights = Field(default_factory=ObjectiveWeights)
    default_timezone: str = Field(default="Asia/Kolkata", description="Default timezone for naive demo inputs")
    allow_unvalidated_fallback: bool = Field(
        default=False,
        description="Whether to recommend with VALIDATION_UNAVAILABLE when Member 4 is unreachable",
    )


# ---------------------------------------------------------------------------
# Input Data Models
# ---------------------------------------------------------------------------

class MaintenanceRequest(BaseModel):
    """Specification of a maintenance block requested by an engineering department."""
    request_id: str = Field(..., min_length=1, description="Unique identifier for the maintenance request")
    track_section_id: str = Field(..., min_length=1, description="Track section where block is required")
    requested_date: Optional[str] = Field(default=None, description="ISO date string for request, if supplied")
    planning_start: datetime = Field(..., description="Start of the planning search horizon")
    planning_end: datetime = Field(..., description="End of the planning search horizon")
    required_duration_minutes: int = Field(..., gt=0, description="Minimum continuous block duration required")
    maintenance_priority: MaintenancePriority = Field(
        default=MaintenancePriority.MEDIUM, description="Operational priority"
    )
    required_resources: List[str] = Field(
        default_factory=list, description="List of required resource IDs/types (e.g. ['TRACK_TEAM_A'])"
    )
    earliest_start_time: Optional[datetime] = Field(
        default=None, description="Earliest permissible window start within planning horizon"
    )
    latest_end_time: Optional[datetime] = Field(
        default=None, description="Latest permissible window end within planning horizon"
    )
    task_dependencies: Optional[List[str]] = Field(
        default=None, description="List of prerequisite maintenance request IDs that must finish prior"
    )
    existing_approved_blocks: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of existing approved block windows on this or adjacent sections"
    )

    @field_validator("request_id", "track_section_id")
    @classmethod
    def check_non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Identifier must not be empty or whitespace.")
        return v.strip()

    @model_validator(mode="after")
    def validate_time_horizons(self) -> MaintenanceRequest:
        if self.planning_end <= self.planning_start:
            raise ValueError(
                f"planning_end ({self.planning_end.isoformat()}) must be strictly after "
                f"planning_start ({self.planning_start.isoformat()})."
            )

        horizon_minutes = (self.planning_end - self.planning_start).total_seconds() / 60.0
        if self.required_duration_minutes > horizon_minutes:
            raise ValueError(
                f"Required duration ({self.required_duration_minutes} mins) exceeds total planning horizon "
                f"({horizon_minutes:.1f} mins from {self.planning_start.isoformat()} to {self.planning_end.isoformat()})."
            )

        if self.earliest_start_time and self.earliest_start_time < self.planning_start:
            raise ValueError("earliest_start_time cannot be earlier than planning_start.")

        if self.latest_end_time and self.latest_end_time > self.planning_end:
            raise ValueError("latest_end_time cannot be later than planning_end.")

        if self.earliest_start_time and self.latest_end_time:
            if self.latest_end_time <= self.earliest_start_time:
                raise ValueError("latest_end_time must be strictly after earliest_start_time.")
            window_minutes = (self.latest_end_time - self.earliest_start_time).total_seconds() / 60.0
            if self.required_duration_minutes > window_minutes:
                raise ValueError(
                    f"Required duration ({self.required_duration_minutes} mins) exceeds window between "
                    f"earliest_start_time and latest_end_time ({window_minutes:.1f} mins)."
                )

        return self


class TrainSchedule(BaseModel):
    """Scheduled train movement through a track section."""
    train_number: str = Field(..., description="Unique train service number (e.g. '12951')")
    train_name: Optional[str] = Field(default=None, description="Commercial train name (e.g. 'Mumbai Rajdhani')")
    source: Optional[str] = Field(default=None, description="Origin station")
    destination: Optional[str] = Field(default=None, description="Destination station")
    track_section_id: str = Field(..., description="Track section traversed by this schedule")
    scheduled_arrival: datetime = Field(..., description="Scheduled arrival or section entry timestamp")
    scheduled_departure: datetime = Field(..., description="Scheduled departure or section exit timestamp")
    train_type: Optional[str] = Field(default="PASSENGER", description="Category: PASSENGER, EXPRESS, FREIGHT, RAJDHANI")
    priority_weight: float = Field(default=1.0, ge=0.1, description="Operational importance weight")

    @model_validator(mode="after")
    def validate_train_times(self) -> TrainSchedule:
        if self.scheduled_departure < self.scheduled_arrival:
            raise ValueError(
                f"scheduled_departure ({self.scheduled_departure}) cannot be before "
                f"scheduled_arrival ({self.scheduled_arrival}) for train {self.train_number}."
            )
        return self


class TrafficDensityRecord(BaseModel):
    """Historical or forecast traffic density for a track section during a time period."""
    track_section_id: str = Field(..., description="Track section identifier")
    start_time: datetime = Field(..., description="Start of density interval")
    end_time: datetime = Field(..., description="End of density interval")
    density_score: float = Field(..., ge=0.0, description="Traffic density score (0.0 to 1.0 or trains/hr)")
    density_category: TrafficDensityCategory = Field(default=TrafficDensityCategory.MEDIUM)

    @model_validator(mode="after")
    def validate_interval(self) -> TrafficDensityRecord:
        if self.end_time <= self.start_time:
            raise ValueError(f"end_time must be after start_time in TrafficDensityRecord for section {self.track_section_id}.")
        return self


class ResourceAvailabilityRecord(BaseModel):
    """Available work crew or specialized equipment interval."""
    resource_id: str = Field(..., description="Resource identifier or type (e.g. 'TRACK_TEAM_A')")
    resource_name: Optional[str] = Field(default=None, description="Human readable name")
    available_start: datetime = Field(..., description="Start of resource availability")
    available_end: datetime = Field(..., description="End of resource availability")
    quantity_available: int = Field(default=1, ge=0, description="Available capacity/quantity")

    @model_validator(mode="after")
    def validate_resource_interval(self) -> ResourceAvailabilityRecord:
        if self.available_end <= self.available_start:
            raise ValueError("available_end must be after available_start in ResourceAvailabilityRecord.")
        return self


class SectionAvailabilityRecord(BaseModel):
    """Section availability status, including closures and maintenance outages."""
    track_section_id: str = Field(..., description="Track section identifier")
    available_start: datetime = Field(..., description="Start of interval")
    available_end: datetime = Field(..., description="End of interval")
    is_blocked: bool = Field(default=False, description="True if section is closed or already reserved")
    block_reason: Optional[str] = Field(default=None, description="Reason if blocked (e.g. 'Pre-approved Block')")

    @model_validator(mode="after")
    def validate_section_interval(self) -> SectionAvailabilityRecord:
        if self.available_end <= self.available_start:
            raise ValueError("available_end must be after available_start in SectionAvailabilityRecord.")
        return self


# ---------------------------------------------------------------------------
# Candidate & Evaluation Models
# ---------------------------------------------------------------------------

class CandidateWindow(BaseModel):
    """A feasible candidate time window generated within the planning horizon."""
    candidate_id: str = Field(..., description="Unique ID for candidate window (e.g. 'CW-001')")
    track_section_id: str = Field(..., description="Track section identifier")
    start_time: datetime = Field(..., description="Proposed window start timestamp")
    end_time: datetime = Field(..., description="Proposed window end timestamp")
    duration_minutes: int = Field(..., gt=0, description="Exact duration in minutes")

    @model_validator(mode="after")
    def validate_window(self) -> CandidateWindow:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time.")
        calc_dur = int(round((self.end_time - self.start_time).total_seconds() / 60.0))
        if calc_dur != self.duration_minutes:
            raise ValueError(f"duration_minutes ({self.duration_minutes}) does not match timestamp difference ({calc_dur}).")
        return self


class DisruptionPrediction(BaseModel):
    """Predicted disruption estimate provided by Member 2 or baseline estimator."""
    candidate_id: str = Field(..., description="ID of evaluated candidate window")
    predicted_delay_minutes: float = Field(..., ge=0.0, description="Estimated total delay in minutes")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Model prediction confidence")
    model_version: str = Field(default="baseline-estimator-v1", description="Identifier of prediction model used")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional prediction metadata")


class ValidationRequest(BaseModel):
    """Data sent to Member 4 for conflict and operational validation."""
    candidate_id: str = Field(..., description="Candidate window identifier")
    track_section_id: str = Field(..., description="Track section")
    start_time: datetime = Field(..., description="Proposed start")
    end_time: datetime = Field(..., description="Proposed end")
    duration_minutes: int = Field(..., description="Duration in minutes")
    affected_trains: List[str] = Field(default_factory=list, description="IDs of potentially affected trains")


class ValidationResult(BaseModel):
    """Validation response received from Member 4."""
    candidate_id: str = Field(..., description="Candidate ID verified")
    status: ValidationStatus = Field(..., description="VALID, CONFLICT, VALIDATION_UNAVAILABLE, or VALIDATION_ERROR")
    reason: Optional[str] = Field(default=None, description="Detailed explanation of conflict or validation status")
    conflict_details: Optional[List[str]] = Field(default=None, description="List of specific conflicting train/block IDs")
    validator_name: str = Field(default="member4-conflict-validator", description="Validator identifier")


class CandidateEvaluation(BaseModel):
    """Comprehensive evaluation metrics and constraint check results for a candidate window."""
    candidate_id: str
    track_section_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    affected_trains: List[str] = Field(default_factory=list, description="Train numbers intersecting this window")
    affected_train_count: int = Field(default=0, ge=0)
    traffic_density_score: float = Field(default=0.0, ge=0.0)
    predicted_delay_minutes: float = Field(default=0.0, ge=0.0)
    resource_feasible: bool = Field(default=True)
    section_feasible: bool = Field(default=True)
    hard_violations: List[str] = Field(default_factory=list, description="List of violated hard constraints")
    is_feasible: bool = Field(default=True, description="True if all hard constraints are satisfied")
    objective_score: float = Field(default=0.0, description="Normalized multi-objective cost (lower is better)")
    score_breakdown: Dict[str, float] = Field(default_factory=dict, description="Individual weighted components")
    explanation: str = Field(default="", description="Detailed human-readable evaluation summary")


# ---------------------------------------------------------------------------
# Output / Response Models
# ---------------------------------------------------------------------------

class RecommendationDetail(BaseModel):
    """Recommended maintenance block details."""
    track_section_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int


class ImpactSummary(BaseModel):
    """Estimated operational impact of the recommended window."""
    affected_train_count: int
    predicted_delay_minutes: Optional[float] = None
    traffic_density: Optional[float] = None
    affected_trains: List[str] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    """Member 4 conflict validation summary."""
    status: ValidationStatus
    reason: Optional[str] = None
    validator_used: Optional[str] = None
    validation_attempts: int = 0


class SolverMetadata(BaseModel):
    """Google OR-Tools solver execution details."""
    status: SolverStatus
    objective_score: Optional[float] = None
    wall_time_seconds: Optional[float] = None
    is_optimal: bool = False


class AlternativeWindow(BaseModel):
    """Ranked alternative maintenance window."""
    rank: int
    candidate_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    objective_score: float
    affected_train_count: int
    predicted_delay_minutes: float
    traffic_density: float
    validation_status: Optional[ValidationStatus] = None


class RejectedCandidateSummary(BaseModel):
    """Summary of rejected candidates and failure reasons."""
    candidate_id: str
    start_time: datetime
    end_time: datetime
    reasons: List[str]


class OptimizationResponse(BaseModel):
    """Top-level response model returned by Member 3 Optimization Engine.
    
    Adheres strictly to the requested schema contract for integration with Member 5.
    """
    status: OptimizationStatus = Field(..., description="Overall optimization outcome")
    request_id: str = Field(..., description="Request identifier")
    recommendation: Optional[RecommendationDetail] = Field(
        default=None, description="Recommended window, present if status == RECOMMENDED"
    )
    estimated_impact: Optional[ImpactSummary] = Field(
        default=None, description="Impact metrics for the recommended window"
    )
    validation: Optional[ValidationSummary] = Field(
        default=None, description="Member 4 validation outcome"
    )
    alternatives: List[AlternativeWindow] = Field(
        default_factory=list, description="Ranked alternative feasible windows"
    )
    rejected_candidates: List[RejectedCandidateSummary] = Field(
        default_factory=list, description="Sample of rejected candidates and reasons"
    )
    explanation: List[str] = Field(
        default_factory=list, description="Human-readable decision rationale"
    )
    solver: Optional[SolverMetadata] = Field(
        default=None, description="Mathematical solver details"
    )
