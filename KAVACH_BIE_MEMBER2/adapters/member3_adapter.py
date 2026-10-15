"""
===============================================================================
KAVACH BIE — Member 2: Integration Adapter for Member 3
Member 3: Optimization & Schedule Ranking Engine
===============================================================================
Provides optimization-oriented interfaces specifically structured for Member 3:
- Single-slot operational disruption evaluation.
- Multi-candidate window comparison and ascending ranking.
- Feasibility filtering by maximum acceptable disruption score.
- Multi-objective Pareto tradeoff analysis (Disruption Score vs. Work Duration).

NOTE: Member 2 predicts disruption and computes exposure scores; Member 3
independently selects the final optimal maintenance block schedule.
"""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from predict_delay import compare_candidate_windows, predict_maintenance_window
from prediction_schema import MaintenanceWindowRequest

logger = logging.getLogger("kavach_bie.adapter.member3")


class Member3OptimizationAdapter:
    """Optimization integration helper for Member 3."""

    @staticmethod
    def evaluate_slot(
        request: Dict[str, Any],
        train_data: Optional[pd.DataFrame] = None,
        traffic_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Evaluate a single proposed maintenance window slot for the optimizer."""
        return predict_maintenance_window(
            request=request,
            train_data=train_data,
            traffic_data=traffic_data,
        )

    @staticmethod
    def rank_candidate_slots(
        candidates: List[Dict[str, Any]],
        train_data: Optional[pd.DataFrame] = None,
        traffic_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Rank multiple candidate slots in ascending order of Disruption Score."""
        return compare_candidate_windows(
            candidates=candidates,
            train_data=train_data,
            traffic_data=traffic_data,
        )

    @staticmethod
    def filter_feasible_slots(
        candidates: List[Dict[str, Any]],
        max_acceptable_score: float = 60.0,
        train_data: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter candidate slots returning only feasible candidates whose
        maintenance exposure score falls below the specified threshold.
        """
        comparison = compare_candidate_windows(candidates, train_data=train_data)
        feasible = []

        for item in comparison["ranked_candidates"]:
            if item.get("is_feasible") and item.get("prediction"):
                score = item["prediction"]["maintenance_exposure_score"]
                if score <= max_acceptable_score:
                    feasible.append(item)

        return feasible

    @staticmethod
    def compute_pareto_tradeoffs(
        candidates: List[Dict[str, Any]],
        train_data: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute Pareto-optimal trade-offs between two competing objectives:
        - Objective 1: Minimize Disruption Score (network friendliness)
        - Objective 2: Maximize Work Possession Duration (engineering productivity)

        Returns list of evaluated candidates annotated with `is_pareto_optimal`.
        """
        comparison = compare_candidate_windows(candidates, train_data=train_data)
        items = [i for i in comparison["ranked_candidates"] if i.get("is_feasible") and i.get("prediction")]

        results = []
        for i, item_a in enumerate(items):
            pred_a = item_a["prediction"]
            score_a = pred_a["maintenance_exposure_score"]
            dur_a = item_a["candidate_summary"].get("required_duration_minutes", 0)

            is_dominated = False
            for j, item_b in enumerate(items):
                if i == j:
                    continue
                pred_b = item_b["prediction"]
                score_b = pred_b["maintenance_exposure_score"]
                dur_b = item_b["candidate_summary"].get("required_duration_minutes", 0)

                # B dominates A if B has <= disruption AND >= duration, with at least one strictly better
                if (score_b <= score_a and dur_b >= dur_a) and (score_b < score_a or dur_b > dur_a):
                    is_dominated = True
                    break

            results.append({
                "request_id": pred_a["request_id"],
                "rank": item_a["rank"],
                "disruption_score": score_a,
                "duration_minutes": dur_a,
                "is_pareto_optimal": not is_dominated,
                "prediction": pred_a,
            })

        return results
