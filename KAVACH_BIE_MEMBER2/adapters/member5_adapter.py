"""
===============================================================================
KAVACH BIE — Member 2: Integration Adapter for Member 5
Member 5: Backend Platform & Operator Dashboard
===============================================================================
Provides a plug-and-play APIRouter that Member 5 can mount directly into
their overarching FastAPI application, or use as a standalone service wrapper.

Mounting Example in Member 5's App:
-----------------------------------
from fastapi import FastAPI
from adapters.member5_adapter import get_member5_router

main_app = FastAPI(title="KAVACH BIE Unified Backend")
main_app.include_router(get_member5_router(), prefix="/api/v1/delays")
"""

import json
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from config import DATA_QUALITY_REPORT_JSON, MODEL_FILE, MODEL_VERSION
from data_validator import DataValidator
from predict_delay import (
    compare_candidate_windows,
    get_member4_validation_context,
    get_model_and_metadata,
    predict_maintenance_window,
)
from prediction_schema import (
    CandidateComparisonResponse,
    MaintenanceWindowRequest,
    Member4ValidationPayload,
    ModelInfoResponse,
    PredictionResponse,
)


def get_member5_router() -> APIRouter:
    """Create and configure the FastAPI APIRouter for Member 5 backend integration."""
    router = APIRouter(tags=["Member 2: Train Delay & Disruption Prediction"])

    @router.get("/health", summary="Service Health & Model Status")
    def health_check():
        model_loaded = MODEL_FILE.exists()
        return {
            "status": "healthy",
            "service": "KAVACH_BIE_MEMBER2",
            "version": MODEL_VERSION,
            "model_loaded": model_loaded,
        }

    @router.get("/model-info", response_model=ModelInfoResponse, summary="Model Metadata & Provenance")
    def get_model_info():
        try:
            _, metadata = get_model_and_metadata()
            champ_m = metadata.get("champion_metrics", {})
            return ModelInfoResponse(
                model_version=metadata.get("model_version", MODEL_VERSION),
                data_source=metadata.get("data_source", "synthetic_railway_demo"),
                prediction_target=metadata.get("prediction_target", "baseline_arrival_delay_minutes"),
                training_timestamp=metadata.get("training_timestamp"),
                best_model_name=metadata.get("best_model_name"),
                metrics={
                    "mae": champ_m.get("mae", 0.0),
                    "rmse": champ_m.get("rmse", 0.0),
                    "r2": champ_m.get("r2", 0.0),
                    "pct_improvement_over_baseline": champ_m.get(
                        "pct_improvement_over_baseline", 0.0
                    ),
                },
                features=metadata.get("feature_columns", []),
                synthetic_data_disclaimer=metadata.get(
                    "synthetic_data_disclaimer", "Trained on synthetic demonstration data."
                ),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read model metadata: {str(exc)}",
            )

    @router.get("/data-quality", summary="Data Quality Audit Report")
    def get_data_quality():
        if DATA_QUALITY_REPORT_JSON.exists():
            with open(DATA_QUALITY_REPORT_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "status": "INITIALIZING",
            "message": "Data quality report not yet generated. Trigger dataset loading to generate.",
        }

    @router.post("/predict", response_model=PredictionResponse, summary="Predict Delay for Maintenance Window")
    def predict_window(request: MaintenanceWindowRequest):
        try:
            result = predict_maintenance_window(request)
            return result
        except ValueError as val_err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inference failed: {str(exc)}")

    @router.post("/compare-windows", response_model=CandidateComparisonResponse, summary="Rank Multiple Candidate Slots")
    def compare_windows(candidates: List[MaintenanceWindowRequest]):
        if not candidates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidates list cannot be empty.")
        try:
            return compare_candidate_windows(candidates)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Comparison failed: {str(exc)}")

    @router.post("/validation-context", response_model=Member4ValidationPayload, summary="Handoff Context for Member 4")
    def get_validation_context(request: MaintenanceWindowRequest):
        try:
            raw_context = get_member4_validation_context(request)
            return Member4ValidationPayload(**raw_context)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return router
