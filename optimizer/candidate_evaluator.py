"""Candidate evaluation and constraint checking for KAVACH BIE Member 3.

Evaluates candidate windows against scheduled train movements, traffic density,
resource calendars, section closures, and delay predictions from Member 2.
Distinguishes between hard constraints and soft objective trade-offs.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Set

from optimizer.data_adapter import BaselineDelayPredictor, DelayPredictorInterface
from optimizer.exceptions import PredictionServiceError
from optimizer.objective import ObjectiveCalculator
from optimizer.schemas import (
    CandidateEvaluation,
    CandidateWindow,
    MaintenanceRequest,
    ObjectiveWeights,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    TrafficDensityRecord,
    TrainSchedule,
)

logger = logging.getLogger(__name__)


def evaluate_candidate(
    candidate: CandidateWindow,
    request: MaintenanceRequest,
    train_data: List[TrainSchedule],
    traffic_data: List[TrafficDensityRecord],
    prediction_service: Optional[DelayPredictorInterface] = None,
    resource_data: Optional[List[ResourceAvailabilityRecord]] = None,
    section_data: Optional[List[SectionAvailabilityRecord]] = None,
    calculator: Optional[ObjectiveCalculator] = None,
    max_delay_reference: float = 60.0,
    max_trains_reference: float = 10.0,
) -> CandidateEvaluation:
    """Evaluate a candidate window against all constraints, train data, traffic, and predictions.

    Args:
        candidate: The candidate time interval to evaluate.
        request: The parent maintenance request with requirements and bounds.
        train_data: List of scheduled train movements.
        traffic_data: Track section traffic density intervals.
        prediction_service: Delay prediction service (Member 2 or baseline).
        resource_data: Available resource capacity intervals.
        section_data: Section closures and existing block records.
        calculator: Objective calculator for scoring.
        max_delay_reference: Normalization reference for delay.
        max_trains_reference: Normalization reference for train count.

    Returns:
        Comprehensive CandidateEvaluation instance.
    """
    if prediction_service is None:
        prediction_service = BaselineDelayPredictor()

    if calculator is None:
        calculator = ObjectiveCalculator(ObjectiveWeights())

    hard_violations: List[str] = []

    # 1. Check Duration Constraint
    if candidate.duration_minutes < request.required_duration_minutes:
        hard_violations.append(
            f"Candidate duration ({candidate.duration_minutes}m) is less than required ({request.required_duration_minutes}m)."
        )

    # 2. Check Planning Horizon Boundaries
    if candidate.start_time < request.planning_start:
        hard_violations.append(
            f"Candidate start ({candidate.start_time.isoformat()}) is before planning_start ({request.planning_start.isoformat()})."
        )
    if candidate.end_time > request.planning_end:
        hard_violations.append(
            f"Candidate end ({candidate.end_time.isoformat()}) is after planning_end ({request.planning_end.isoformat()})."
        )
    if request.earliest_start_time and candidate.start_time < request.earliest_start_time:
        hard_violations.append(
            f"Candidate start ({candidate.start_time.isoformat()}) violates earliest_start_time ({request.earliest_start_time.isoformat()})."
        )
    if request.latest_end_time and candidate.end_time > request.latest_end_time:
        hard_violations.append(
            f"Candidate end ({candidate.end_time.isoformat()}) violates latest_end_time ({request.latest_end_time.isoformat()})."
        )

    # 3. Check Scheduled Train Movements (Overlap Detection)
    affected_train_set: Set[str] = set()
    for train in train_data:
        if train.track_section_id == candidate.track_section_id:
            # Overlap check
            overlap_start = max(train.scheduled_arrival, candidate.start_time)
            overlap_end = min(train.scheduled_departure, candidate.end_time)
            if overlap_start < overlap_end:
                affected_train_set.add(train.train_number)
            elif train.scheduled_arrival == train.scheduled_departure:
                # Instantaneous train pass-through check
                if candidate.start_time <= train.scheduled_arrival <= candidate.end_time:
                    affected_train_set.add(train.train_number)

    affected_trains = sorted(list(affected_train_set))
    affected_train_count = len(affected_trains)

    # 4. Compute Traffic Density
    section_densities: List[float] = []
    for td in traffic_data:
        if td.track_section_id == candidate.track_section_id:
            overlap_start = max(td.start_time, candidate.start_time)
            overlap_end = min(td.end_time, candidate.end_time)
            if overlap_start < overlap_end:
                section_densities.append(td.density_score)

    avg_traffic_density = (
        sum(section_densities) / len(section_densities) if section_densities else 0.3
    )

    # 5. Check Resource Availability
    resource_feasible = True
    if request.required_resources:
        if not resource_data:
            resource_feasible = False
            hard_violations.append(
                f"Resource calendar missing; required resources {request.required_resources} cannot be verified."
            )
        else:
            for required_res in request.required_resources:
                # Find if any active availability covers the entire candidate window
                has_resource = False
                for r in resource_data:
                    if (
                        r.resource_id == required_res
                        and r.available_start <= candidate.start_time
                        and r.available_end >= candidate.end_time
                        and r.quantity_available >= 1
                    ):
                        has_resource = True
                        break
                if not has_resource:
                    resource_feasible = False
                    hard_violations.append(
                        f"Required resource '{required_res}' is unavailable during window {candidate.start_time.strftime('%H:%M')}-{candidate.end_time.strftime('%H:%M')}."
                    )

    # 6. Check Section Availability & Pre-approved Blocks
    section_feasible = True
    if section_data:
        for sec in section_data:
            if sec.track_section_id == candidate.track_section_id and sec.is_blocked:
                overlap_start = max(sec.available_start, candidate.start_time)
                overlap_end = min(sec.available_end, candidate.end_time)
                if overlap_start < overlap_end:
                    section_feasible = False
                    reason_text = sec.block_reason or "Section is closed / unavailable"
                    hard_violations.append(
                        f"Track section {candidate.track_section_id} is blocked: {reason_text}."
                    )

    # Check request's existing approved blocks list if present
    if request.existing_approved_blocks:
        for blk in request.existing_approved_blocks:
            blk_sec = blk.get("track_section_id", candidate.track_section_id)
            if blk_sec == candidate.track_section_id:
                try:
                    b_start = blk["start_time"]
                    b_end = blk["end_time"]
                    if isinstance(b_start, str):
                        from optimizer.data_adapter import normalize_datetime
                        b_start = normalize_datetime(b_start)
                        b_end = normalize_datetime(b_end)
                    if max(b_start, candidate.start_time) < min(b_end, candidate.end_time):
                        section_feasible = False
                        hard_violations.append(
                            f"Window overlaps existing approved block ({blk.get('block_id', 'Pre-approved')})."
                        )
                except Exception as exc:
                    logger.warning("Could not parse existing approved block: %s", exc)

    # 7. Predict Disruption & Delay
    try:
        prediction = prediction_service.predict_disruption(
            candidate, train_data, traffic_data
        )
        predicted_delay_minutes = prediction.predicted_delay_minutes
    except PredictionServiceError:
        raise
    except Exception as exc:
        logger.error("Failed to predict disruption for %s: %s", candidate.candidate_id, exc)
        raise PredictionServiceError(
            f"Prediction failed for candidate {candidate.candidate_id}: {exc}",
            details={"candidate_id": candidate.candidate_id},
        ) from exc

    # 8. Feasibility & Scoring
    is_feasible = (len(hard_violations) == 0)

    score, breakdown = calculator.compute_score(
        candidate=candidate,
        request=request,
        predicted_delay_minutes=predicted_delay_minutes,
        affected_train_count=affected_train_count,
        traffic_density_score=avg_traffic_density,
        max_delay_reference=max_delay_reference,
        max_trains_reference=max_trains_reference,
    )

    # Build human-readable evaluation explanation
    if is_feasible:
        explanation = (
            f"Candidate {candidate.candidate_id} ({candidate.start_time.strftime('%H:%M')}-{candidate.end_time.strftime('%H:%M')}): "
            f"Feasible. Impacts {affected_train_count} train(s) {affected_trains or '[]'}, "
            f"traffic density {avg_traffic_density:.2f}, predicted delay {predicted_delay_minutes:.1f} mins, score {score:.4f}."
        )
    else:
        explanation = (
            f"Candidate {candidate.candidate_id} ({candidate.start_time.strftime('%H:%M')}-{candidate.end_time.strftime('%H:%M')}): "
            f"Infeasible due to {len(hard_violations)} hard constraint violation(s): {'; '.join(hard_violations)}."
        )

    return CandidateEvaluation(
        candidate_id=candidate.candidate_id,
        track_section_id=candidate.track_section_id,
        start_time=candidate.start_time,
        end_time=candidate.end_time,
        duration_minutes=candidate.duration_minutes,
        affected_trains=affected_trains,
        affected_train_count=affected_train_count,
        traffic_density_score=round(avg_traffic_density, 3),
        predicted_delay_minutes=round(predicted_delay_minutes, 2),
        resource_feasible=resource_feasible,
        section_feasible=section_feasible,
        hard_violations=hard_violations,
        is_feasible=is_feasible,
        objective_score=score,
        score_breakdown=breakdown,
        explanation=explanation,
    )
