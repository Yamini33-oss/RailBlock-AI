"""FastAPI Router and integration endpoint for Member 5 backend integration.

Provides the REST API contract for KAVACH BIE Member 3 Optimization Engine.
Can be mounted directly into Member 5's FastAPI application:
    from optimizer.api import optimizer_router
    app.include_router(optimizer_router)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from optimizer.data_adapter import DataLoader
from optimizer.schemas import (
    MaintenanceRequest,
    OptimizationResponse,
    OptimizationStatus,
    PlanningConfig,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    TrafficDensityRecord,
    TrainSchedule,
)
from optimizer.service import optimize_maintenance_window

logger = logging.getLogger(__name__)

optimizer_router = APIRouter(
    prefix="/api/optimization",
    tags=["Member 3 — AI Block Planning & Optimization Engine"],
)


class OptimizationApiRequest(BaseModel):
    """Payload sent by Member 5 backend to trigger block optimization."""
    request_id: str = Field(..., description="Unique maintenance request ID (e.g. 'MR-001')")
    track_section_id: str = Field(..., description="Track section identifier (e.g. 'SEC-01')")
    planning_start: str = Field(..., description="ISO datetime string for horizon start")
    planning_end: str = Field(..., description="ISO datetime string for horizon end")
    required_duration_minutes: int = Field(..., gt=0, description="Required block duration in minutes")
    maintenance_priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, EMERGENCY")
    required_resources: List[str] = Field(default_factory=list, description="List of required resource IDs")
    earliest_start_time: Optional[str] = Field(default=None, description="Optional earliest start")
    latest_end_time: Optional[str] = Field(default=None, description="Optional latest end")
    task_dependencies: Optional[List[str]] = Field(default=None)
    existing_approved_blocks: Optional[List[Dict[str, Any]]] = Field(default=None)

    # Optional overrides for datasets; if omitted, default synthetic datasets are used
    train_data: Optional[List[Dict[str, Any]]] = None
    traffic_data: Optional[List[Dict[str, Any]]] = None
    resource_data: Optional[List[Dict[str, Any]]] = None
    section_data: Optional[List[Dict[str, Any]]] = None

    # Solver configuration
    config: Optional[PlanningConfig] = None

    # Integration toggles: if True, calls real Member 2 / Member 4 services
    use_real_validator: Optional[bool] = Field(
        default=None,
        description="If True, validate candidates using live Member 4 service. Defaults to env var OPTIMIZER_USE_MEMBER4 or False.",
    )
    use_real_predictor: Optional[bool] = Field(
        default=None,
        description="If True, query live Member 2 prediction service. Defaults to env var OPTIMIZER_USE_MEMBER2 or False.",
    )


@optimizer_router.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, Any]:
    """Health check for Member 3 Optimization Engine and OR-Tools availability."""
    try:
        from ortools.sat.python import cp_model
        ortools_status = "READY"
    except Exception as exc:
        ortools_status = f"UNAVAILABLE: {exc}"

    return {
        "module": "Member 3 — AI Block Planning and Optimization Engine",
        "status": "HEALTHY",
        "solver": "Google OR-Tools CP-SAT",
        "solver_readiness": ortools_status,
        "api_version": "1.0.0",
    }


@optimizer_router.post(
    "/recommend",
    response_model=OptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend optimal maintenance block window",
)
def recommend_maintenance_window(payload: OptimizationApiRequest) -> OptimizationResponse:
    """Generate, evaluate, optimize, and validate maintenance block windows.

    Applies Google OR-Tools CP-SAT constraint programming, calls Member 2's delay predictor,
    and submits the best candidates to Member 4's operational validator.
    """
    from optimizer.data_adapter import normalize_datetime

    # Parse maintenance request
    try:
        req = MaintenanceRequest(
            request_id=payload.request_id,
            track_section_id=payload.track_section_id,
            planning_start=normalize_datetime(payload.planning_start),
            planning_end=normalize_datetime(payload.planning_end),
            required_duration_minutes=payload.required_duration_minutes,
            maintenance_priority=payload.maintenance_priority.upper(),
            required_resources=payload.required_resources,
            earliest_start_time=normalize_datetime(payload.earliest_start_time) if payload.earliest_start_time else None,
            latest_end_time=normalize_datetime(payload.latest_end_time) if payload.latest_end_time else None,
            task_dependencies=payload.task_dependencies,
            existing_approved_blocks=payload.existing_approved_blocks,
        )
    except Exception as exc:
        logger.error("Failed to construct MaintenanceRequest: %s", exc)
        return OptimizationResponse(
            status=OptimizationStatus.INVALID_REQUEST,
            request_id=payload.request_id,
            explanation=[f"Input validation error: {exc}"],
        )

    # Ingest datasets (custom or synthetic defaults)
    data_dir = Path(__file__).parent.parent / "data" / "synthetic"
    
    train_schedules = payload.train_data
    if train_schedules is None and (data_dir / "train_schedule.csv").exists():
        train_schedules = DataLoader.load_train_schedules(data_dir / "train_schedule.csv")

    traffic_records = payload.traffic_data
    if traffic_records is None and (data_dir / "traffic_density.csv").exists():
        traffic_records = DataLoader.load_traffic_density(data_dir / "traffic_density.csv")

    resource_records = payload.resource_data
    if resource_records is None and (data_dir / "resource_availability.csv").exists():
        resource_records = DataLoader.load_resource_availability(data_dir / "resource_availability.csv")

    section_records = payload.section_data
    if section_records is None and (data_dir / "section_availability.csv").exists():
        section_records = DataLoader.load_section_availability(data_dir / "section_availability.csv")

    input_data = {
        "train_data": train_schedules or [],
        "traffic_data": traffic_records or [],
        "resource_data": resource_records or [],
        "section_data": section_records or [],
    }

    import os
    from optimizer.data_adapter import BaselineDelayPredictor, Member2PredictorAdapter
    from optimizer.member2_client import predict_candidate_window
    from optimizer.validation_client import Member4HTTPClient, MockMember4Validator

    # Determine validator: Member4HTTPClient or MockMember4Validator
    use_member4 = payload.use_real_validator
    if use_member4 is None:
        use_member4 = os.getenv("OPTIMIZER_USE_MEMBER4", "false").lower() in ("true", "1", "yes")

    if use_member4:
        member4_base_url = os.getenv("MEMBER4_BASE_URL", "http://127.0.0.1:8004")
        validator = Member4HTTPClient(
            base_url=member4_base_url,
            required_resources=req.required_resources or ["Maintenance Team"],
        )
    else:
        validator = MockMember4Validator()

    # Determine predictor: Member2PredictorAdapter or BaselineDelayPredictor
    use_member2 = payload.use_real_predictor
    if use_member2 is None:
        use_member2 = os.getenv("OPTIMIZER_USE_MEMBER2", "false").lower() in ("true", "1", "yes")

    if use_member2:
        priority_val = req.maintenance_priority.value if hasattr(req.maintenance_priority, "value") else str(req.maintenance_priority)
        def member2_predictor(candidate_window, candidate_train_data, candidate_traffic_data):
            return predict_candidate_window(
                candidate_window,
                candidate_train_data,
                candidate_traffic_data,
                maintenance_priority=priority_val,
            )
        predictor = Member2PredictorAdapter(
            predictor_callable=member2_predictor,
            fallback_to_baseline=True,
        )
    else:
        predictor = BaselineDelayPredictor()

    response = optimize_maintenance_window(
        request=req,
        input_data=input_data,
        config=payload.config or PlanningConfig(),
        predictor=predictor,
        validator=validator,
    )

    return response


# Standalone runner
app = FastAPI(
    title="KAVACH BIE — Member 3 AI Block Planning and Optimization Engine",
    description="Automated railway maintenance block scheduling via Google OR-Tools CP-SAT.",
    version="1.0.0",
)
app.include_router(optimizer_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("optimizer.api:app", host="0.0.0.0", port=8003, reload=True)
