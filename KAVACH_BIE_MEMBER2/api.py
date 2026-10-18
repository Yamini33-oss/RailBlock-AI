"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Optional FastAPI Integration Adapter for Member 5
===============================================================================
Exposes Member 2's prediction engine via high-performance REST endpoints:
- GET  /health          : Service and model artifact health check.
- GET  /model-info      : Provenance, performance metrics, and feature metadata.
- POST /predict         : Predict corridor delay & disruption score for a window.
- POST /compare-windows : Evaluate and rank candidate maintenance blocks.

Can be run standalone:
    uvicorn api:app --reload --port 8000
Or mounted by Member 5:
    from api import app as delay_service_app
    parent_app.mount("/delays", delay_service_app)
"""

from typing import List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
from pathlib import Path

_MEMBER2_DIR = Path(__file__).resolve().parent
if str(_MEMBER2_DIR) not in sys.path:
    sys.path.insert(0, str(_MEMBER2_DIR))

from config import MODEL_FILE, MODEL_VERSION
from predict_delay import (
    compare_candidate_windows,
    get_model_and_metadata,
    predict_maintenance_window,
)
from prediction_schema import (
    CandidateComparisonResponse,
    MaintenanceWindowRequest,
    ModelInfoResponse,
    PredictionResponse,
)

app = FastAPI(
    title="KAVACH BIE — Train Delay Prediction API",
    description=(
        "Advanced AI/ML service for predicting corridor delays and calculating "
        "operational disruption scores for railway track maintenance block planning."
    ),
    version=MODEL_VERSION,
)

# Enable CORS for local web interface integration (Member 5 frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check():
    """Health and model availability status check."""
    model_loaded = MODEL_FILE.exists()
    return {
        "status": "healthy",
        "service": "KAVACH_BIE_MEMBER2",
        "version": MODEL_VERSION,
        "model_loaded": model_loaded,
    }


@app.get("/model-info", response_model=ModelInfoResponse, tags=["Metadata"])
def get_model_info():
    """Retrieve metadata, evaluation metrics, and feature schemas of the active model."""
    try:
        _, metadata = get_model_and_metadata()
        champion_metrics = metadata.get("champion_metrics", {})
        return ModelInfoResponse(
            model_version=metadata.get("model_version", MODEL_VERSION),
            data_source=metadata.get("data_source", "synthetic_railway_demo"),
            prediction_target=metadata.get("prediction_target", "historical_delay_minutes"),
            training_timestamp=metadata.get("training_timestamp"),
            best_model_name=metadata.get("best_model_name"),
            metrics={
                "mae": champion_metrics.get("mae", 0.0),
                "rmse": champion_metrics.get("rmse", 0.0),
                "r2": champion_metrics.get("r2", 0.0),
                "pct_improvement_over_baseline": champion_metrics.get(
                    "pct_improvement_over_baseline", 0.0
                ),
            },
            features=metadata.get("feature_columns", []),
            synthetic_data_disclaimer=metadata.get(
                "synthetic_data_disclaimer",
                "Model trained on synthetic demonstration data.",
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model metadata: {str(exc)}",
        )


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict_window(request: MaintenanceWindowRequest):
    """
    Predict train delay, affected train count, and disruption score for a candidate maintenance window.
    """
    try:
        result = predict_maintenance_window(request)
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(exc)}",
        )


@app.post("/compare-windows", response_model=CandidateComparisonResponse, tags=["Optimization"])
def compare_windows(candidates: List[MaintenanceWindowRequest]):
    """
    Evaluate multiple candidate windows and return them ranked by Ascending Disruption Score.
    """
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidates list cannot be empty.",
        )
    try:
        comparison_result = compare_candidate_windows(candidates)
        return comparison_result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison evaluation failed: {str(exc)}",
        )


@app.get("/data-quality", tags=["Data Quality"])
def get_data_quality():
    """Retrieve the latest data quality audit report."""
    from config import DATA_QUALITY_REPORT_JSON
    import json

    if DATA_QUALITY_REPORT_JSON.exists():
        with open(DATA_QUALITY_REPORT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "status": "INITIALIZING",
        "message": "Data quality report not yet generated. Load datasets to trigger audit.",
    }


@app.post("/validation-context", tags=["Operational Validation"])
def get_validation_context(request: MaintenanceWindowRequest):
    """Expose schedule collision and headway context for Member 4 validation."""
    from predict_delay import get_member4_validation_context
    try:
        return get_member4_validation_context(request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))



if __name__ == "__main__":
    print(f"[*] Starting KAVACH BIE Delay Prediction API on http://127.0.0.1:8000 ...")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
