"""Pydantic schemas for optimization jobs, candidates, and validation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from optimizer.schemas import (
    AlternativeWindow,
    ImpactSummary,
    OptimizationResponse,
    OptimizationStatus,
    PlanningConfig,
    RecommendationDetail,
    SolverMetadata,
    ValidationStatus,
    ValidationSummary,
)


class OptimizationJobCreate(BaseModel):
    """Payload to trigger an optimization job."""
    request_id: str = Field(..., description="Maintenance request identifier")
    config: Optional[PlanningConfig] = None
    use_real_datasets: bool = Field(default=True, description="Whether to evaluate against real railway timetable datasets")
    custom_train_data: Optional[List[Dict[str, Any]]] = None
    custom_traffic_data: Optional[List[Dict[str, Any]]] = None


class OptimizationJobStatusResponse(BaseModel):
    """Status of an asynchronous or synchronous optimization job."""
    job_id: str
    request_id: str
    status: str = Field(..., description="QUEUED, RUNNING, COMPLETED, FAILED")
    created_at: str
    updated_at: str
    result: Optional[OptimizationResponse] = None
    error: Optional[str] = None


class JobValidationSubmit(BaseModel):
    """Submit a recommended candidate from a job to Member 4 for validation."""
    job_id: str
    candidate_id: str
    override_validator_url: Optional[str] = None
