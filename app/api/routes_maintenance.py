"""Maintenance request endpoints for KAVACH BIE Member 3."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.firebase_auth import get_current_user
from app.adapters.firestore_repository import firestore_repo
from app.schemas.maintenance import MaintenanceRequestCreate, MaintenanceRequestResponse
from optimizer.data_adapter import normalize_datetime
from optimizer.schemas import MaintenancePriority, MaintenanceRequest

router = APIRouter(prefix="/api/v1/maintenance-requests", tags=["Maintenance Requests"])


@router.post("", response_model=MaintenanceRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_maintenance_request(
    payload: MaintenanceRequestCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> MaintenanceRequestResponse:
    """Submit and store a new railway maintenance block request."""
    # Validate with Pydantic domain validator
    try:
        p_start = normalize_datetime(payload.planning_start)
        p_end = normalize_datetime(payload.planning_end)
        e_start = normalize_datetime(payload.earliest_start_time) if payload.earliest_start_time else None
        l_end = normalize_datetime(payload.latest_end_time) if payload.latest_end_time else None

        req = MaintenanceRequest(
            request_id=payload.request_id,
            track_section_id=payload.track_section_id,
            planning_start=p_start,
            planning_end=p_end,
            required_duration_minutes=payload.required_duration_minutes,
            maintenance_priority=payload.maintenance_priority,
            required_resources=payload.required_resources,
            earliest_start_time=e_start,
            latest_end_time=l_end,
            task_dependencies=payload.task_dependencies,
            existing_approved_blocks=payload.existing_approved_blocks,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid request parameters: {exc}") from exc

    # Persist in Cloud Firestore
    doc_payload = {
        "request_id": payload.request_id,
        "track_section_id": payload.track_section_id,
        "planning_start": payload.planning_start,
        "planning_end": payload.planning_end,
        "required_duration_minutes": payload.required_duration_minutes,
        "maintenance_priority": payload.maintenance_priority.value,
        "required_resources": payload.required_resources,
        "earliest_start_time": payload.earliest_start_time,
        "latest_end_time": payload.latest_end_time,
        "description": payload.description,
        "created_by": current_user.get("uid", "anonymous"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    saved_doc = firestore_repo.save_maintenance_request(payload.request_id, doc_payload)

    firestore_repo.log_audit_event(
        user_id=current_user.get("uid", "anonymous"),
        action="MAINTENANCE_REQUEST_CREATED",
        details={"request_id": payload.request_id, "section": payload.track_section_id},
    )

    return MaintenanceRequestResponse(
        request_id=saved_doc["request_id"],
        track_section_id=saved_doc["track_section_id"],
        planning_start=saved_doc["planning_start"],
        planning_end=saved_doc["planning_end"],
        required_duration_minutes=saved_doc["required_duration_minutes"],
        maintenance_priority=saved_doc["maintenance_priority"],
        required_resources=saved_doc.get("required_resources", []),
        description=saved_doc.get("description"),
        created_at=saved_doc.get("created_at"),
        updated_at=saved_doc.get("updated_at"),
    )


@router.get("", response_model=List[MaintenanceRequestResponse], status_code=status.HTTP_200_OK)
def list_maintenance_requests(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[MaintenanceRequestResponse]:
    """List recent maintenance requests recorded in Firestore."""
    docs = firestore_repo.list_maintenance_requests(limit=limit)
    return [
        MaintenanceRequestResponse(
            request_id=d["request_id"],
            track_section_id=d["track_section_id"],
            planning_start=d["planning_start"],
            planning_end=d["planning_end"],
            required_duration_minutes=d["required_duration_minutes"],
            maintenance_priority=d.get("maintenance_priority", "MEDIUM"),
            required_resources=d.get("required_resources", []),
            description=d.get("description"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
        )
        for d in docs
    ]


@router.get("/{request_id}", response_model=MaintenanceRequestResponse, status_code=status.HTTP_200_OK)
def get_maintenance_request(
    request_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> MaintenanceRequestResponse:
    """Retrieve details for a specific maintenance request."""
    doc = firestore_repo.get_maintenance_request(request_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maintenance request '{request_id}' not found.")

    return MaintenanceRequestResponse(
        request_id=doc["request_id"],
        track_section_id=doc["track_section_id"],
        planning_start=doc["planning_start"],
        planning_end=doc["planning_end"],
        required_duration_minutes=doc["required_duration_minutes"],
        maintenance_priority=doc.get("maintenance_priority", "MEDIUM"),
        required_resources=doc.get("required_resources", []),
        description=doc.get("description"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )
