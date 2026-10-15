"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Inference Engine and Candidate Window Comparison
===============================================================================
Provides the primary public API for Member 3's optimization engine:
- `predict_maintenance_window(...)`: Evaluates a single proposed block window.
- `compare_candidate_windows(...)`: Evaluates and ranks multiple candidate slots.

Derives:
1. Baseline corridor delay (minutes).
2. Affected scheduled train count (timetabled overlap + safety buffer).
3. Corridor traffic density.
4. Composite Disruption Score (0-100+).
5. Operational Risk Category (LOW, MEDIUM, HIGH, CRITICAL).
6. Uncertainty bounds (derived via ensemble variance).
7. Feature explainability breakdown.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
import pandas as pd

from config import (
    DEFAULT_SAFETY_BUFFER_MINUTES,
    METADATA_FILE,
    MODEL_FILE,
    PRIORITY_MULTIPLIERS,
    RISK_THRESHOLDS,
    WEIGHT_AFFECTED_TRAINS,
    WEIGHT_DELAY,
    WEIGHT_DENSITY,
    WEIGHT_DURATION,
)
from data_loader import DataLoader
from data_validator import (
    DataValidator,
    calculate_window_span_minutes,
    parse_time_to_minutes,
)
from feature_engineering import (
    build_inference_feature_row,
    extract_temporal_features,
)
from prediction_schema import MaintenanceWindowRequest, PredictionResponse

logger = logging.getLogger("kavach_bie.predict")

# Cached pipeline & metadata in memory for low-latency inference
_CACHED_PIPELINE = None
_CACHED_METADATA = None
_CACHED_SCHEDULES = None
_CACHED_TRAFFIC = None


def get_model_and_metadata() -> Tuple[Any, Dict[str, Any]]:
    """Retrieve or lazily load the trained pipeline and metadata."""
    global _CACHED_PIPELINE, _CACHED_METADATA
    if _CACHED_PIPELINE is None or _CACHED_METADATA is None:
        if not MODEL_FILE.exists() or not METADATA_FILE.exists():
            logger.info("Model artifact not found. Triggering auto-training pipeline...")
            from train_model import run_training_pipeline
            run_training_pipeline()

        logger.info("Loading model artifact from %s...", MODEL_FILE)
        _CACHED_PIPELINE = joblib.load(MODEL_FILE)
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            _CACHED_METADATA = json.load(f)

    return _CACHED_PIPELINE, _CACHED_METADATA


def get_cached_schedules_and_traffic() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Retrieve or lazily load timetables and traffic logs for real-time inference."""
    global _CACHED_SCHEDULES, _CACHED_TRAFFIC
    if _CACHED_SCHEDULES is None or _CACHED_TRAFFIC is None:
        loader = DataLoader(auto_generate=True)
        _CACHED_SCHEDULES = loader.load_schedules()
        _CACHED_TRAFFIC = loader.load_traffic()
    return _CACHED_SCHEDULES, _CACHED_TRAFFIC


def calculate_affected_trains(
    track_section: str,
    start_time_str: str,
    end_time_str: str,
    schedules_df: Optional[pd.DataFrame] = None,
    buffer_minutes: int = DEFAULT_SAFETY_BUFFER_MINUTES,
) -> int:
    """
    Count timetabled trains traversing the track section whose schedule overlaps
    with the proposed maintenance window plus the specified safety buffer.
    """
    if schedules_df is None:
        schedules_df, _ = get_cached_schedules_and_traffic()

    section_trains = schedules_df[schedules_df["track_section"] == track_section]
    if len(section_trains) == 0:
        return 0

    w_start = parse_time_to_minutes(start_time_str)
    w_end = parse_time_to_minutes(end_time_str)
    if w_start is None or w_end is None:
        return 0

    # Expand window by buffer
    buf_start = (w_start - buffer_minutes) % 1440
    buf_end = (w_end + buffer_minutes) % 1440
    is_overnight = w_end < w_start

    affected_count = 0
    for _, train in section_trains.iterrows():
        t_arr = parse_time_to_minutes(train["scheduled_arrival"])
        t_dep = parse_time_to_minutes(train["scheduled_departure"])
        if t_arr is None or t_dep is None:
            continue

        # Check interval overlap
        if not is_overnight:
            overlaps = max(w_start - buffer_minutes, t_arr) <= min(w_end + buffer_minutes, t_dep)
        else:
            # Window spans past midnight
            part1 = max(w_start - buffer_minutes, t_arr) <= min(1440, t_dep)
            part2 = max(0, t_arr) <= min(w_end + buffer_minutes, t_dep)
            overlaps = part1 or part2

        if overlaps:
            affected_count += 1

    return affected_count


def calculate_disruption_score(
    predicted_delay_minutes: float,
    traffic_density: float,
    affected_train_count: int,
    duration_minutes: float,
    priority: str,
) -> float:
    """
    Compute the standardized KAVACH Disruption Score (0.0 to 100+).

    Formula:
    Score = [ (Delay * W_delay) +
              (Density * 20 * W_density) +
              (AffectedTrains * 10 * W_trains) +
              ((Duration/60) * 5 * W_duration) ] * PriorityMultiplier
    """
    priority_mult = PRIORITY_MULTIPLIERS.get(priority.upper(), 1.0)
    delay_component = max(0.0, predicted_delay_minutes) * WEIGHT_DELAY
    density_component = traffic_density * 20.0 * WEIGHT_DENSITY
    trains_component = affected_train_count * 10.0 * WEIGHT_AFFECTED_TRAINS
    duration_component = (duration_minutes / 60.0) * 5.0 * WEIGHT_DURATION

    raw_score = (delay_component + density_component + trains_component + duration_component) * priority_mult
    return round(float(raw_score), 2)


def classify_risk_category(disruption_score: float) -> str:
    """Classify disruption score into documented operational risk brackets."""
    for category, (low, high) in RISK_THRESHOLDS.items():
        if low <= disruption_score < high:
            return category
    return "CRITICAL"


def estimate_uncertainty(
    pipeline: Any,
    feature_row: pd.DataFrame,
    predicted_value: float,
) -> Dict[str, Any]:
    """
    Estimate uncertainty interval using the variance across individual trees
    if the pipeline's regressor is an ensemble (e.g. RandomForestRegressor).
    """
    regressor = pipeline.named_steps.get("regressor")
    preprocessor = pipeline.named_steps.get("preprocessor")

    if hasattr(regressor, "estimators_") and len(regressor.estimators_) > 0:
        transformed_row = preprocessor.transform(feature_row)
        tree_predictions = [float(tree.predict(transformed_row)[0]) for tree in regressor.estimators_]
        std_error = float(np.std(tree_predictions))

        # ~90% prediction interval (z = 1.645)
        lower_bound = max(0.0, round(predicted_value - 1.645 * std_error, 1))
        upper_bound = round(predicted_value + 1.645 * std_error, 1)

        return {
            "available": True,
            "lower_bound_minutes": lower_bound,
            "upper_bound_minutes": upper_bound,
            "confidence_level": 0.90,
            "method": "RandomForest_Ensemble_Variance",
            "reason": (
                "Estimated via dispersion across individual decision trees in the ensemble. "
                "Synthetic dataset variance; field operational variance may differ."
            ),
        }

    # Fallback to test residual RMSE if ensemble trees are not present (e.g. RidgeRegression)
    if _CACHED_METADATA and "champion_metrics" in _CACHED_METADATA:
        rmse = float(_CACHED_METADATA["champion_metrics"].get("rmse", 16.0))
        lower_bound = max(0.0, round(predicted_value - 1.645 * rmse, 1))
        upper_bound = round(predicted_value + 1.645 * rmse, 1)
        return {
            "available": True,
            "lower_bound_minutes": lower_bound,
            "upper_bound_minutes": upper_bound,
            "confidence_level": 0.90,
            "method": "Holdout_Test_Residual_RMSE",
            "reason": (
                f"Estimated via holdout test residual RMSE ({rmse:.2f} mins) at ~90% confidence. "
                "Derived from synthetic training data; actual field variance may differ."
            ),
        }

    return {
        "available": False,
        "lower_bound_minutes": None,
        "upper_bound_minutes": None,
        "confidence_level": None,
        "method": "Unavailable",
        "reason": "Current active model architecture does not support parametric intervals.",
    }



def generate_feature_explanations(
    traffic_density: float,
    affected_trains: int,
    duration_minutes: float,
    time_period: str,
    priority: str,
) -> List[Dict[str, Any]]:
    """Generate interpretable factor attributions for the prediction."""
    explanations = []

    # Traffic Density impact
    if traffic_density >= 0.75:
        explanations.append(
            {
                "feature_name": "traffic_density",
                "feature_value": round(traffic_density, 3),
                "importance_score": 0.28,
                "impact_direction": "INCREASES_DELAY",
                "description": f"High corridor traffic density ({traffic_density:.2f}) limits track possession flexibility.",
            }
        )
    else:
        explanations.append(
            {
                "feature_name": "traffic_density",
                "feature_value": round(traffic_density, 3),
                "importance_score": 0.28,
                "impact_direction": "DECREASES_DELAY",
                "description": f"Moderate to low corridor traffic density ({traffic_density:.2f}) provides spare headway buffer.",
            }
        )

    # Affected trains
    if affected_trains > 3:
        explanations.append(
            {
                "feature_name": "affected_train_count",
                "feature_value": affected_trains,
                "importance_score": 0.25,
                "impact_direction": "INCREASES_DELAY",
                "description": f"{affected_trains} scheduled services conflict with the requested block window.",
            }
        )
    else:
        explanations.append(
            {
                "feature_name": "affected_train_count",
                "feature_value": affected_trains,
                "importance_score": 0.25,
                "impact_direction": "DECREASES_DELAY",
                "description": f"Minimal scheduled train conflict ({affected_trains} services) during window.",
            }
        )

    # Time of day
    if "PEAK" in time_period:
        explanations.append(
            {
                "feature_name": "time_period",
                "feature_value": time_period,
                "importance_score": 0.22,
                "impact_direction": "INCREASES_DELAY",
                "description": f"Requested window falls within {time_period}, when corridor congestion is naturally highest.",
            }
        )
    else:
        explanations.append(
            {
                "feature_name": "time_period",
                "feature_value": time_period,
                "importance_score": 0.22,
                "impact_direction": "DECREASES_DELAY",
                "description": f"Requested window falls during off-peak hours ({time_period}), lowering cascade risk.",
            }
        )

    # Duration
    explanations.append(
        {
            "feature_name": "required_duration_minutes",
            "feature_value": duration_minutes,
            "importance_score": 0.15,
            "impact_direction": "INCREASES_DELAY" if duration_minutes > 180 else "NEUTRAL",
            "description": f"Track possession duration of {duration_minutes:.0f} minutes.",
        }
    )

    return explanations


# -----------------------------------------------------------------------------
# Main Public Interface Functions
# -----------------------------------------------------------------------------
def predict_maintenance_window(
    request: Union[Dict[str, Any], MaintenanceWindowRequest],
    train_data: Optional[pd.DataFrame] = None,
    traffic_data: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Evaluate a single proposed maintenance window and return structured predictions.

    Parameters:
    -----------
    request : dict or MaintenanceWindowRequest
        Maintenance window request containing track section, date, times, and duration.
    train_data : pd.DataFrame, optional
        Custom timetable schedules (defaults to sample schedules).
    traffic_data : pd.DataFrame, optional
        Custom traffic density observations (defaults to sample traffic).

    Returns:
    --------
    dict conforming to PredictionResponse schema.
    """
    # Normalize input
    if isinstance(request, MaintenanceWindowRequest):
        raw_req = request.model_dump()
    elif isinstance(request, dict):
        raw_req = request.copy()
    else:
        raise ValueError(f"Request must be a dict or MaintenanceWindowRequest, got {type(request).__name__}.")

    # Validate and clean request using detailed validator
    validator = DataValidator()
    sanitized_req, warnings, imputations, is_ood = validator.validate_single_request_detailed(raw_req)

    # Retrieve model pipeline & metadata
    pipeline, metadata = get_model_and_metadata()

    # Load data context if not passed
    default_sched, default_traffic = get_cached_schedules_and_traffic()
    schedules_df = train_data if train_data is not None else default_sched
    traffic_df = traffic_data if traffic_data is not None else default_traffic

    track_sec = sanitized_req["track_section"]
    req_date = sanitized_req["requested_date"]
    start_time = sanitized_req["proposed_start_time"]
    end_time = sanitized_req["proposed_end_time"]
    duration = sanitized_req["required_duration_minutes"]
    priority = sanitized_req["maintenance_priority"]

    # 1. Affected Train Count
    affected_trains = calculate_affected_trains(
        track_section=track_sec,
        start_time_str=start_time,
        end_time_str=end_time,
        schedules_df=schedules_df,
    )

    # 2. Traffic Density Resolution
    temp_info = extract_temporal_features(req_date, start_time)
    resolved_density = sanitized_req.get("traffic_density")
    if resolved_density is None:
        matches = traffic_df[
            (traffic_df["track_section"] == track_sec)
            & (traffic_df["time_period"] == temp_info["time_period"])
        ]
        if len(matches) > 0:
            resolved_density = float(matches["traffic_density"].median())
        else:
            resolved_density = 0.65
            warnings.append(
                f"No specific traffic log found for {track_sec} during {temp_info['time_period']}; defaulted to {resolved_density}."
            )
    resolved_density = round(resolved_density, 3)

    # Operational metrics
    scheduled_train_count = max(affected_trains, 4)
    track_utilization = round(resolved_density * 1.05, 3)
    rolling_delay = sanitized_req.get("existing_delay_minutes") or 8.5

    # 3. Model Inference (ML predicted delay minutes)
    feature_row = build_inference_feature_row(
        request_dict=sanitized_req,
        traffic_density=resolved_density,
        scheduled_train_count=scheduled_train_count,
        track_utilization=track_utilization,
        rolling_avg_delay=rolling_delay,
    )

    pred_delay_raw = float(pipeline.predict(feature_row)[0])
    predicted_delay = max(0.0, round(pred_delay_raw, 1))

    # 4. Disruption Score / Maintenance Exposure Score
    disruption_score = calculate_disruption_score(
        predicted_delay_minutes=predicted_delay,
        traffic_density=resolved_density,
        affected_train_count=affected_trains,
        duration_minutes=duration,
        priority=priority,
    )

    # 5. Risk Category
    risk_category = classify_risk_category(disruption_score)

    # 6. Uncertainty Estimation
    uncertainty_dict = estimate_uncertainty(pipeline, feature_row, predicted_delay)

    # 7. Feature Explanations
    explanations = generate_feature_explanations(
        traffic_density=resolved_density,
        affected_trains=affected_trains,
        duration_minutes=duration,
        time_period=temp_info["time_period"],
        priority=priority,
    )

    # Additional operational advisory warnings
    if "PEAK" in temp_info["time_period"]:
        warnings.append(f"Window overlaps {temp_info['time_period']}; high likelihood of timetable congestion.")
    if duration > 240.0:
        warnings.append(f"Extended block duration ({duration} mins) exceeds typical 4-hr daylight work slot.")

    # Data quality assessment
    dq_status = "OUT_OF_DISTRIBUTION" if is_ood else ("WARNING" if (warnings or imputations) else "VALID")
    data_quality_info = {
        "status": dq_status,
        "warnings": warnings,
        "imputations": imputations,
        "is_out_of_distribution": is_ood,
    }

    response = {
        "request_id": sanitized_req["request_id"],
        "model_version": metadata.get("model_version", "1.1.0"),
        "data_source": metadata.get("data_source", "synthetic_railway_demo"),
        "prediction_target": "baseline_arrival_delay_minutes",
        "predicted_baseline_delay_minutes": predicted_delay,
        "predicted_delay_minutes": predicted_delay,  # Backward compatibility alias
        "affected_train_count": affected_trains,
        "traffic_density": resolved_density,
        "maintenance_exposure_score": disruption_score,
        "disruption_score": disruption_score,  # Backward compatibility alias
        "risk_category": risk_category,
        "uncertainty": uncertainty_dict,
        "data_quality": data_quality_info,
        "explanation": explanations,
        "warnings": warnings,
        "errors": [],
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(
        "Prediction for %s: Delay=%.1fm, AffectedTrains=%d, DisruptionScore=%.1f, Risk=%s",
        sanitized_req["request_id"],
        predicted_delay,
        affected_trains,
        disruption_score,
        risk_category,
    )
    return response


def compare_candidate_windows(
    candidates: List[Union[Dict[str, Any], MaintenanceWindowRequest]],
    train_data: Optional[pd.DataFrame] = None,
    traffic_data: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Evaluate and rank multiple candidate maintenance windows for the same or different requests.
    Feasible candidates are ranked in ascending order of Disruption Score.
    Infeasible candidates that fail data/duration checks are NOT dropped; they are preserved
    with is_feasible=False and diagnostics, enabling Member 3 to make informed decisions.
    """
    if not candidates:
        raise ValueError("Candidates list cannot be empty.")

    feasible_items = []
    infeasible_items = []

    for cand in candidates:
        cand_dict = cand.model_dump() if isinstance(cand, MaintenanceWindowRequest) else dict(cand)
        req_id = str(cand_dict.get("request_id", "UNKNOWN"))

        try:
            pred_dict = predict_maintenance_window(
                request=cand,
                train_data=train_data,
                traffic_data=traffic_data,
            )
            feasible_items.append({
                "is_feasible": True,
                "validation_errors": [],
                "prediction": pred_dict,
                "candidate_summary": cand_dict,
                "score": pred_dict["maintenance_exposure_score"],
            })
        except Exception as exc:
            infeasible_items.append({
                "is_feasible": False,
                "validation_errors": [str(exc)],
                "prediction": None,
                "candidate_summary": cand_dict,
                "score": float("inf"),
            })

    # Sort feasible candidates by ascending disruption score
    feasible_items.sort(key=lambda x: x["score"])

    ranked_candidates = []
    rank_idx = 1
    for item in feasible_items:
        ranked_candidates.append({
            "rank": rank_idx,
            "is_recommended": (rank_idx == 1),
            "is_feasible": True,
            "validation_errors": [],
            "prediction": item["prediction"],
            "candidate_summary": item["candidate_summary"],
        })
        rank_idx += 1

    for item in infeasible_items:
        ranked_candidates.append({
            "rank": rank_idx,
            "is_recommended": False,
            "is_feasible": False,
            "validation_errors": item["validation_errors"],
            "prediction": None,
            "candidate_summary": item["candidate_summary"],
        })
        rank_idx += 1

    recommended_id = (
        ranked_candidates[0]["prediction"]["request_id"]
        if feasible_items and ranked_candidates[0]["prediction"]
        else None
    )

    return {
        "total_candidates": len(ranked_candidates),
        "feasible_candidates": len(feasible_items),
        "infeasible_candidates": len(infeasible_items),
        "recommended_request_id": recommended_id,
        "ranked_candidates": ranked_candidates,
        "ranking_criterion": "Ascending Disruption Score (Feasible candidates prioritized; Infeasible candidates reported with errors)",
    }


def get_member4_validation_context(
    request: Union[Dict[str, Any], MaintenanceWindowRequest],
    train_data: Optional[pd.DataFrame] = None,
    buffer_minutes: int = DEFAULT_SAFETY_BUFFER_MINUTES,
) -> Dict[str, Any]:
    """
    Assemble the detailed operational and schedule collision context for Member 4's
    safety certification and interlocking conflict checks.
    """
    raw_req = request.model_dump() if isinstance(request, MaintenanceWindowRequest) else dict(request)
    prediction = predict_maintenance_window(raw_req, train_data=train_data)

    default_sched, _ = get_cached_schedules_and_traffic()
    schedules_df = train_data if train_data is not None else default_sched

    track_sec = raw_req["track_section"]
    start_str = raw_req["proposed_start_time"]
    end_str = raw_req["proposed_end_time"]

    w_start = parse_time_to_minutes(start_str)
    w_end = parse_time_to_minutes(end_str)
    is_overnight = w_end < w_start if (w_start and w_end) else False

    section_trains = schedules_df[schedules_df["track_section"] == track_sec]
    conflicts = []

    for _, train in section_trains.iterrows():
        t_arr = parse_time_to_minutes(train.get("scheduled_arrival"))
        t_dep = parse_time_to_minutes(train.get("scheduled_departure"))
        if t_arr is None or t_dep is None or w_start is None or w_end is None:
            continue

        if not is_overnight:
            overlaps = max(w_start - buffer_minutes, t_arr) <= min(w_end + buffer_minutes, t_dep)
        else:
            part1 = max(w_start - buffer_minutes, t_arr) <= min(1440, t_dep)
            part2 = max(0, t_arr) <= min(w_end + buffer_minutes, t_dep)
            overlaps = part1 or part2

        if overlaps:
            conflicts.append({
                "train_number": str(train.get("train_number")),
                "train_name": str(train.get("train_name")),
                "scheduled_arrival": str(train.get("scheduled_arrival")),
                "scheduled_departure": str(train.get("scheduled_departure")),
                "source": str(train.get("source", "N/A")),
                "destination": str(train.get("destination", "N/A")),
            })

    return {
        "request_id": raw_req["request_id"],
        "track_section": track_sec,
        "requested_date": raw_req["requested_date"],
        "proposed_start_time": start_str,
        "proposed_end_time": end_str,
        "required_duration_minutes": float(raw_req["required_duration_minutes"]),
        "affected_train_count": len(conflicts),
        "conflicting_trains": conflicts,
        "predicted_baseline_delay_minutes": prediction["predicted_baseline_delay_minutes"],
        "maintenance_exposure_score": prediction["maintenance_exposure_score"],
        "risk_category": prediction["risk_category"],
        "safety_buffer_applied_minutes": buffer_minutes,
        "data_quality_status": prediction["data_quality"]["status"],
        "operational_warnings": prediction["warnings"],
        "disclaimer": (
            "Member 2 provides operational delay estimates and schedule overlaps. "
            "Member 4 must independently certify safety clearance, signal interlocking, and traction power isolation."
        ),
    }

