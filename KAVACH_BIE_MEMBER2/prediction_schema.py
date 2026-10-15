"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Pydantic Data Schemas and Validation Models (Upgraded v1.1.0)
===============================================================================
Defines strongly typed, validated request and response data models used
across the core prediction engine, Member 1 data adapter, Member 3 optimization
interface, Member 4 conflict handoff, and the Member 5 dashboard API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class MaintenanceWindowRequest(BaseModel):
    """Input specification for proposing a track maintenance window."""

    request_id: str = Field(
        ...,
        description="Unique identifier for the maintenance request (e.g. 'REQ_BLK_001')",
        examples=["REQ_BLK_001"],
    )
    track_section: str = Field(
        ...,
        description="Corridor or track section code (e.g. 'SEC_NDLS_CNB')",
        examples=["SEC_NDLS_CNB"],
    )
    requested_date: str = Field(
        ...,
        description="Target date in ISO format YYYY-MM-DD",
        examples=["2026-10-20"],
    )
    proposed_start_time: str = Field(
        ...,
        description="Block start time in 24-hour HH:MM format",
        examples=["01:30"],
    )
    proposed_end_time: str = Field(
        ...,
        description="Block end time in 24-hour HH:MM format",
        examples=["04:30"],
    )
    required_duration_minutes: float = Field(
        ...,
        gt=0,
        le=1440,
        description="Required track possession duration in minutes (max 24 hours / 1440 mins)",
        examples=[180.0],
    )
    maintenance_priority: Optional[str] = Field(
        default="MEDIUM",
        description="Priority level: CRITICAL, HIGH, MEDIUM, or LOW",
        examples=["HIGH"],
    )
    traffic_density: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Optional pre-calculated traffic density (0.0 to 1.5+). If omitted, inferred from logs.",
        examples=[0.65],
    )
    existing_delay_minutes: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Optional known rolling delay (in minutes) on the corridor before block execution.",
        examples=[12.0],
    )

    @field_validator("maintenance_priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> str:
        if v is None:
            return "MEDIUM"
        normalized = v.strip().upper()
        allowed = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if normalized not in allowed:
            raise ValueError(
                f"Invalid maintenance_priority '{v}'. Allowed values are: {sorted(list(allowed))}"
            )
        return normalized

    @field_validator("requested_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        v_str = v.strip()
        try:
            datetime.strptime(v_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format '{v}'. Expected ISO format 'YYYY-MM-DD' (e.g. '2026-10-20')."
            )
        return v_str


class UncertaintyInfo(BaseModel):
    """Estimated uncertainty interval and method details."""

    available: bool = Field(
        ...,
        description="Indicates whether calibrated or ensemble uncertainty could be calculated.",
    )
    lower_bound_minutes: Optional[float] = Field(
        default=None,
        description="Estimated lower bound of predicted baseline delay (minutes)",
    )
    upper_bound_minutes: Optional[float] = Field(
        default=None,
        description="Estimated upper bound of predicted baseline delay (minutes)",
    )
    confidence_level: Optional[float] = Field(
        default=None,
        description="Nominal confidence level (e.g. 0.90 for ~90% interval)",
    )
    method: str = Field(
        ...,
        description="Method used to derive bounds (e.g. 'Holdout_Test_Residual_RMSE' or 'RandomForest_Ensemble_Variance')",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Explanation or caveats regarding uncertainty estimation.",
    )


class DataQualityInfo(BaseModel):
    """Data quality and integrity audit for an individual prediction."""

    status: str = Field(
        default="VALID",
        description="Status: 'VALID', 'WARNING', or 'OUT_OF_DISTRIBUTION'",
    )
    warnings: List[str] = Field(default_factory=list)
    imputations: List[str] = Field(default_factory=list)
    is_out_of_distribution: bool = False


class FeatureExplanation(BaseModel):
    """Explainability breakdown for an individual feature's contribution."""

    feature_name: str
    feature_value: Any
    importance_score: Optional[float] = None
    impact_direction: str = Field(
        ...,
        description="Indicates expected influence: 'INCREASES_DELAY', 'DECREASES_DELAY', or 'NEUTRAL'",
    )
    description: str


class PredictionResponse(BaseModel):
    """Standardized prediction output payload returned to Member 3 and Member 5."""

    request_id: str
    model_version: str
    data_source: str
    prediction_target: str = Field(
        default="baseline_arrival_delay_minutes",
        description="Explicit prediction target: expected baseline section delay",
    )
    predicted_baseline_delay_minutes: float = Field(
        ...,
        description="ML-estimated expected baseline delay in minutes under current conditions",
    )
    predicted_delay_minutes: float = Field(
        ...,
        description="Backward-compatible alias for predicted_baseline_delay_minutes",
    )
    affected_train_count: int
    traffic_density: float
    maintenance_exposure_score: float = Field(
        ...,
        description="Multi-factor operational disruption score (0-100+)",
    )
    disruption_score: float = Field(
        ...,
        description="Backward-compatible alias for maintenance_exposure_score",
    )
    risk_category: str
    uncertainty: UncertaintyInfo
    data_quality: DataQualityInfo
    explanation: List[FeatureExplanation]
    warnings: List[str]
    errors: List[str] = Field(default_factory=list)
    timestamp: str


class CandidateComparisonItem(BaseModel):
    """A single evaluated candidate window within a ranked comparison."""

    rank: int
    is_recommended: bool
    is_feasible: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    prediction: Optional[PredictionResponse] = None
    candidate_summary: Dict[str, Any] = Field(default_factory=dict)


class CandidateComparisonResponse(BaseModel):
    """Ranked comparison output for Member 3's optimization engine."""

    total_candidates: int
    feasible_candidates: int
    infeasible_candidates: int
    recommended_request_id: Optional[str]
    ranked_candidates: List[CandidateComparisonItem]
    ranking_criterion: str


class Member4ValidationPayload(BaseModel):
    """Handoff data package for Member 4's operational conflict and interlocking verification."""

    request_id: str
    track_section: str
    requested_date: str
    proposed_start_time: str
    proposed_end_time: str
    required_duration_minutes: float
    affected_train_count: int
    conflicting_trains: List[Dict[str, Any]]
    predicted_baseline_delay_minutes: float
    maintenance_exposure_score: float
    risk_category: str
    safety_buffer_applied_minutes: int
    data_quality_status: str
    operational_warnings: List[str]
    disclaimer: str = (
        "Member 2 provides operational delay estimates and schedule overlaps. "
        "Member 4 must independently certify safety clearance, signal interlocking, and traction power isolation."
    )


class ModelInfoResponse(BaseModel):
    """Metadata detailing the trained model, training provenance, and evaluation metrics."""

    model_version: str
    data_source: str
    prediction_target: str
    training_timestamp: Optional[str]
    best_model_name: Optional[str]
    metrics: Dict[str, float]
    features: List[str]
    synthetic_data_disclaimer: str
