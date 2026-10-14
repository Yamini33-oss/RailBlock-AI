"""Multi-criteria objective calculation and scoring for KAVACH BIE Member 3.

Provides normalized scoring across delay, affected train movements,
traffic density, block duration slack, and maintenance priority urgency.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from optimizer.schemas import (
    CandidateWindow,
    MaintenancePriority,
    MaintenanceRequest,
    ObjectiveWeights,
)

logger = logging.getLogger(__name__)


class ObjectiveCalculator:
    """Calculates normalized objective scores and component breakdowns for candidate windows."""

    def __init__(self, weights: ObjectiveWeights) -> None:
        self.weights = weights
        self._norm_weights = weights.normalized()

    def compute_score(
        self,
        candidate: CandidateWindow,
        request: MaintenanceRequest,
        predicted_delay_minutes: float,
        affected_train_count: int,
        traffic_density_score: float,
        max_delay_reference: float = 60.0,
        max_trains_reference: float = 10.0,
    ) -> Tuple[float, Dict[str, float]]:
        """Compute the weighted multi-objective cost score for a candidate window.

        Lower score represents a more desirable, less disruptive maintenance window.

        Args:
            candidate: CandidateWindow under evaluation.
            request: MaintenanceRequest providing priority and planning boundaries.
            predicted_delay_minutes: Delay in minutes predicted by Member 2 or baseline.
            affected_train_count: Number of trains intersecting this window.
            traffic_density_score: Average traffic density in [0.0, 1.0].
            max_delay_reference: Scaling denominator for delay normalization.
            max_trains_reference: Scaling denominator for affected trains normalization.

        Returns:
            Tuple of (total_score, score_breakdown_dict).
        """
        # 1. Normalized Delay Component [0.0, 1.0]
        denom_delay = max(max_delay_reference, 1.0)
        norm_delay = min(max(predicted_delay_minutes / denom_delay, 0.0), 1.0)

        # 2. Normalized Affected Trains Component [0.0, 1.0]
        denom_trains = max(max_trains_reference, 1.0)
        norm_trains = min(max(affected_train_count / denom_trains, 0.0), 1.0)

        # 3. Normalized Traffic Density Component [0.0, 1.0]
        norm_density = min(max(traffic_density_score, 0.0), 1.0)

        # 4. Normalized Slack Duration Component [0.0, 1.0]
        # In our generator, candidate.duration == request.required_duration_minutes, so slack is typically 0
        slack_minutes = max(candidate.duration_minutes - request.required_duration_minutes, 0)
        norm_slack = min(slack_minutes / 60.0, 1.0)

        # 5. Priority Urgency Component [0.0, 1.0]
        # How far into the planning horizon is this candidate?
        total_horizon_seconds = (request.planning_end - request.planning_start).total_seconds()
        start_offset_seconds = (candidate.start_time - request.planning_start).total_seconds()
        horizon_fraction = start_offset_seconds / total_horizon_seconds if total_horizon_seconds > 0 else 0.0
        horizon_fraction = min(max(horizon_fraction, 0.0), 1.0)

        # Priority multipliers:
        # EMERGENCY: Strongly penalizes later slots (must be scheduled immediately)
        # HIGH: Moderately penalizes later slots
        # MEDIUM: Mild scheduling preference
        # LOW: No urgency penalty (0.0)
        urgency_multiplier = {
            MaintenancePriority.EMERGENCY: 1.0,
            MaintenancePriority.HIGH: 0.6,
            MaintenancePriority.MEDIUM: 0.3,
            MaintenancePriority.LOW: 0.0,
        }.get(request.maintenance_priority, 0.3)

        norm_urgency = horizon_fraction * urgency_multiplier

        # Weighted combination
        w_delay = self._norm_weights["weight_delay"]
        w_trains = self._norm_weights["weight_trains"]
        w_density = self._norm_weights["weight_traffic_density"]
        w_slack = self._norm_weights["weight_slack_duration"]
        w_urgency = self._norm_weights["weight_priority_urgency"]

        part_delay = w_delay * norm_delay
        part_trains = w_trains * norm_trains
        part_density = w_density * norm_density
        part_slack = w_slack * norm_slack
        part_urgency = w_urgency * norm_urgency

        total_score = part_delay + part_trains + part_density + part_slack + part_urgency

        breakdown = {
            "predicted_delay_contribution": round(part_delay, 4),
            "affected_trains_contribution": round(part_trains, 4),
            "traffic_density_contribution": round(part_density, 4),
            "slack_duration_contribution": round(part_slack, 4),
            "priority_urgency_contribution": round(part_urgency, 4),
            "raw_predicted_delay_minutes": round(predicted_delay_minutes, 2),
            "raw_affected_train_count": affected_train_count,
            "raw_traffic_density": round(traffic_density_score, 3),
        }

        return round(total_score, 4), breakdown
