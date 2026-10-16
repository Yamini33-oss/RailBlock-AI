
"""HTTP client for the KAVACH BIE Member 2 prediction service."""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

MEMBER2_PREDICTION_URL = os.getenv(
    "MEMBER2_PREDICTION_URL",
    "http://127.0.0.1:8005/predict",
)

REQUEST_TIMEOUT_SECONDS = 10


def predict_candidate_window(
    candidate_window: Any,
    train_data: Any,
    traffic_data: Any,
    maintenance_priority: str = "MEDIUM",
) -> dict:
    """Request a disruption prediction for one optimizer candidate."""

    start_time = candidate_window.start_time
    end_time = candidate_window.end_time

    payload = {
        "request_id": str(candidate_window.candidate_id),
        "track_section": str(candidate_window.track_section_id),
        "requested_date": start_time.strftime("%Y-%m-%d"),
        "proposed_start_time": start_time.strftime("%H:%M"),
        "proposed_end_time": end_time.strftime("%H:%M"),
        "required_duration_minutes": int(
            candidate_window.duration_minutes
        ),
        "maintenance_priority": str(maintenance_priority).upper(),
    }

    try:
        response = requests.post(
            MEMBER2_PREDICTION_URL,
            json=payload,
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()

    except requests.RequestException as exc:
        logger.error("Member 2 API request failed: %s", exc)
        raise RuntimeError(
            f"Member 2 prediction API is unavailable: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError("Member 2 returned an invalid response.")

    if result.get("errors"):
        raise RuntimeError(
            f"Member 2 prediction errors: {result['errors']}"
        )

    if "predicted_delay_minutes" not in result:
        raise RuntimeError(
            "Member 2 response is missing predicted_delay_minutes."
        )

    return {
        "predicted_delay_minutes": float(
            result["predicted_delay_minutes"]
        ),
        "confidence": 1.0,
        "model_version": str(
            result.get("model_version", "member2-model")
        ),
        "details": {
            "data_source": result.get("data_source"),
            "predicted_baseline_delay_minutes": result.get(
                "predicted_baseline_delay_minutes"
            ),
            "affected_train_count": result.get("affected_train_count"),
            "disruption_score": result.get("disruption_score"),
            "risk_category": result.get("risk_category"),
            "uncertainty": result.get("uncertainty"),
            "data_quality": result.get("data_quality"),
            "explanation": result.get("explanation"),
            "warnings": result.get("warnings", []),
        },
    }
