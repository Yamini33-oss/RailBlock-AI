"""Health check and system diagnostics endpoint for KAVACH BIE Member 3."""

from typing import Any, Dict
from fastapi import APIRouter, status

from app.adapters.firestore_repository import firestore_repo
from app.adapters.storage_repository import storage_repo
from app.config import settings

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health", status_code=status.HTTP_200_OK)
def get_system_health() -> Dict[str, Any]:
    """Retrieve operational health, Google OR-Tools solver status, and Firebase connection details."""
    try:
        from ortools.sat.python import cp_model
        solver_status = "READY"
    except Exception as exc:
        solver_status = f"UNAVAILABLE: {exc}"

    return {
        "status": "HEALTHY",
        "service": "KAVACH BIE — Member 3 AI Block Planning & Optimization Engine",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "solver": {
            "name": "Google OR-Tools CP-SAT",
            "readiness": solver_status,
        },
        "firebase": {
            "project_id": settings.FIREBASE_PROJECT_ID,
            "configured": settings.is_firebase_configured,
            "firestore_mode": "LIVE_CLOUD_FIRESTORE" if firestore_repo.is_configured else "IN_MEMORY_MOCK",
            "storage_mode": "FIREBASE_CLOUD_STORAGE" if storage_repo.is_configured else "LOCAL_FILESYSTEM",
            "auth_enforced": settings.FIREBASE_AUTH_ENABLED,
        },
        "datasets": {
            "processed_dir": str(settings.DATA_PROCESSED_DIR),
            "stations_available": (settings.DATA_PROCESSED_DIR / "stations_processed.csv").exists(),
            "trains_available": (settings.DATA_PROCESSED_DIR / "trains_processed.csv").exists(),
            "schedules_available": (settings.DATA_PROCESSED_DIR / "schedules_processed.csv").exists(),
            "density_available": (settings.DATA_PROCESSED_DIR / "section_traffic_density_processed.csv").exists(),
        },
    }
