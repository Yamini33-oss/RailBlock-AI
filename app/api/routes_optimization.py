"""Optimization job execution, inspection, and Member 4 validation routes."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.firebase_auth import get_current_user
from app.adapters.firestore_repository import firestore_repo
from app.schemas.optimization import (
    JobValidationSubmit,
    OptimizationJobCreate,
    OptimizationJobStatusResponse,
)
from app.services.recommendation_service import recommendation_service
from optimizer.schemas import CandidateEvaluation, ValidationResult, ValidationStatus
from optimizer.validation_client import Member4HTTPClient, MockMember4Validator

router = APIRouter(prefix="/api/v1/optimization", tags=["Optimization Engine & Jobs"])


@router.post("/run", response_model=OptimizationJobStatusResponse, status_code=status.HTTP_200_OK)
def run_optimization_job(
    payload: OptimizationJobCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> OptimizationJobStatusResponse:
    """Trigger an optimization job for a maintenance request.

    Evaluates candidate windows against real railway schedules or custom datasets,
    solves multi-criteria integer programming via Google OR-Tools CP-SAT, and logs
    results to Cloud Firestore and Firebase Cloud Messaging.
    """
    try:
        job_result = recommendation_service.run_optimization_job(payload, current_user)
        return OptimizationJobStatusResponse(
            job_id=job_result["job_id"],
            request_id=job_result["request_id"],
            status=job_result["status"],
            created_at=job_result["created_at"],
            updated_at=job_result["updated_at"],
            result=job_result.get("result"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Optimization error: {exc}") from exc


@router.get("/{job_id}", response_model=OptimizationJobStatusResponse, status_code=status.HTTP_200_OK)
def get_optimization_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> OptimizationJobStatusResponse:
    """Retrieve the execution status and recommended window of an optimization job."""
    job_doc = firestore_repo.get_optimization_job(job_id)
    if not job_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Optimization job '{job_id}' not found.")

    res_doc = firestore_repo.get_optimization_result(job_id)

    return OptimizationJobStatusResponse(
        job_id=job_doc["job_id"],
        request_id=job_doc.get("request_id", ""),
        status=job_doc.get("status", "UNKNOWN"),
        created_at=job_doc.get("created_at", ""),
        updated_at=job_doc.get("updated_at", ""),
        result=res_doc,
        error=job_doc.get("error"),
    )


@router.get("/{job_id}/candidates", status_code=status.HTTP_200_OK)
def get_job_candidates(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all evaluated candidate windows, ranked alternatives, and scores for a job."""
    res_doc = firestore_repo.get_optimization_result(job_id)
    if not res_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No results found for optimization job '{job_id}'.")

    return {
        "job_id": job_id,
        "recommendation": res_doc.get("recommendation"),
        "estimated_impact": res_doc.get("estimated_impact"),
        "alternatives": res_doc.get("alternatives", []),
        "rejected_candidates": res_doc.get("rejected_candidates", []),
        "solver": res_doc.get("solver"),
    }


@router.post("/{job_id}/validate", status_code=status.HTTP_200_OK)
def validate_job_recommendation(
    payload: JobValidationSubmit,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Submit a recommended candidate from a job to Member 4 for operational validation."""
    res_doc = firestore_repo.get_optimization_result(payload.job_id)
    if not res_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{payload.job_id}' not found.")

    rec = res_doc.get("recommendation")
    if not rec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job has no recommended window to validate.")

    # Formulate validation request
    cand_eval = CandidateEvaluation(
        candidate_id=payload.candidate_id,
        track_section_id=rec["track_section_id"],
        start_time=rec["start_time"],
        end_time=rec["end_time"],
        duration_minutes=rec["duration_minutes"],
        affected_train_count=res_doc.get("estimated_impact", {}).get("affected_train_count", 0),
        affected_trains=res_doc.get("estimated_impact", {}).get("affected_trains", []),
    )

    if payload.override_validator_url:
        validator = Member4HTTPClient(base_url=payload.override_validator_url)
    else:
        validator = MockMember4Validator()

    val_res = validator.validate_candidate(cand_eval)

    # Persist validation outcome to Firestore
    val_record = {
        "job_id": payload.job_id,
        "candidate_id": payload.candidate_id,
        "status": val_res.status.value,
        "reason": val_res.reason,
        "validator_name": val_res.validator_name,
        "validated_by_user": current_user.get("uid"),
    }
    validation_id = f"val-{payload.job_id}-{payload.candidate_id}"
    firestore_repo.save_validation_result(validation_id, val_record)

    # Update job result validation field
    res_doc["validation"] = {
        "status": val_res.status.value,
        "reason": val_res.reason,
        "validator_used": val_res.validator_name,
        "validation_attempts": res_doc.get("validation", {}).get("validation_attempts", 1),
    }
    firestore_repo.save_optimization_result(payload.job_id, res_doc)

    return {
        "validation_id": validation_id,
        "job_id": payload.job_id,
        "candidate_id": payload.candidate_id,
        "validation_status": val_res.status.value,
        "reason": val_res.reason,
        "validator": val_res.validator_name,
    }
