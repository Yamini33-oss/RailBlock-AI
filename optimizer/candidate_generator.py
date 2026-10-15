"""Candidate maintenance window generator for KAVACH BIE Member 3.

Generates candidate maintenance intervals within a requested planning horizon,
respecting step intervals, duration requirements, earliest start, and latest end constraints.
Handles midnight crossings, multi-day horizons, and timezone consistency.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from optimizer.exceptions import InvalidRequestError
from optimizer.schemas import CandidateWindow, MaintenanceRequest, PlanningConfig

logger = logging.getLogger(__name__)


def generate_candidate_windows(
    request: MaintenanceRequest,
    config: Optional[PlanningConfig] = None,
) -> List[CandidateWindow]:
    """Generate discrete candidate maintenance windows for a given request.

    Args:
        request: Validated MaintenanceRequest.
        config: Optional planning configuration containing step_minutes.

    Returns:
        List of CandidateWindow instances within the planning boundaries.

    Raises:
        InvalidRequestError: If time boundaries are invalid or reversed.
    """
    if config is None:
        config = PlanningConfig()

    step_minutes = config.step_minutes
    if step_minutes <= 0:
        raise InvalidRequestError(
            f"PlanningConfig.step_minutes must be positive, got {step_minutes}."
        )

    # Effective search boundaries
    search_start = request.planning_start
    search_end = request.planning_end

    if request.earliest_start_time:
        search_start = max(search_start, request.earliest_start_time)

    if request.latest_end_time:
        search_end = min(search_end, request.latest_end_time)

    if search_end <= search_start:
        logger.warning(
            "Effective planning window is non-positive for request %s (start: %s, end: %s)",
            request.request_id,
            search_start.isoformat(),
            search_end.isoformat(),
        )
        return []

    required_duration = timedelta(minutes=request.required_duration_minutes)
    effective_horizon = search_end - search_start

    if required_duration > effective_horizon:
        logger.warning(
            "Required duration (%s) exceeds effective horizon (%s) for request %s.",
            required_duration,
            effective_horizon,
            request.request_id,
        )
        return []

    step = timedelta(minutes=step_minutes)
    candidates: List[CandidateWindow] = []
    seen_intervals = set()

    current_start = search_start
    counter = 1

    # Generate candidate windows stepping forward
    while current_start + required_duration <= search_end:
        current_end = current_start + required_duration

        # Ensure window is within all hard constraints
        # 1. Must start on or after planning_start and earliest_start_time
        # 2. Must end on or before planning_end and latest_end_time
        if current_start >= request.planning_start and current_end <= request.planning_end:
            if request.earliest_start_time and current_start < request.earliest_start_time:
                current_start += step
                continue
            if request.latest_end_time and current_end > request.latest_end_time:
                break

            interval_key = (current_start, current_end)
            if interval_key not in seen_intervals:
                seen_intervals.add(interval_key)
                cand_id = f"CW-{counter:03d}"
                candidate = CandidateWindow(
                    candidate_id=cand_id,
                    track_section_id=request.track_section_id,
                    start_time=current_start,
                    end_time=current_end,
                    duration_minutes=request.required_duration_minutes,
                )
                candidates.append(candidate)
                counter += 1

        current_start += step

    logger.info(
        "Generated %d candidate windows for request %s on section %s (duration: %d mins, step: %d mins)",
        len(candidates),
        request.request_id,
        request.track_section_id,
        request.required_duration_minutes,
        step_minutes,
    )
    return candidates
