"""
===============================================================================
KAVACH BIE — Cross-Member Mock Implementations
Mock Subsystems for Members 1, 3, 4, and 5
===============================================================================
Provides mock implementations of the other 4 team modules to enable:
- Standalone development without depending on incomplete peer modules.
- End-to-end contract validation tests.
- Offline demonstration during hackathon judging.
"""

from typing import Any, Dict, List
import pandas as pd

from adapters.member1_adapter import Member1DataAdapter
from adapters.member3_adapter import Member3OptimizationAdapter
from adapters.member4_adapter import Member4ValidationAdapter
from prediction_schema import MaintenanceWindowRequest, Member4ValidationPayload


class MockMember1DataIngestion:
    """Simulates Member 1 feeding uncleaned, raw external CSVs with arbitrary column names."""

    @staticmethod
    def get_raw_external_delays_dataframe() -> pd.DataFrame:
        """Simulate Member 1's upstream database export with non-canonical aliases."""
        return pd.DataFrame(
            [
                {
                    "train_no": "12002",
                    "train_name": "Shatabdi Express",
                    "date": "2026-09-15",
                    "section_code": "SEC_NDLS_CNB",
                    "sch_arr": "06:00",
                    "act_arr": "06:14",
                    "sch_dep": "10:15",
                    "act_dep": "10:31",
                    "delay_mins": 16.0,
                },
                {
                    "train_no": "12951",
                    "train_name": "Tejas Rajdhani",
                    "date": "2026-09-15",
                    "section_code": "SEC_BCT_ST",
                    "sch_arr": "17:00",
                    "act_arr": "17:05",
                    "sch_dep": "19:43",
                    "act_dep": "19:49",
                    "delay_mins": 6.0,
                },
            ]
        )


class MockMember3OptimizationEngine:
    """Simulates Member 3 submitting 4 candidate windows for an emergency work order."""

    def __init__(self):
        self.adapter = Member3OptimizationAdapter()

    def find_best_maintenance_slot(self, track_section: str, target_date: str) -> Dict[str, Any]:
        """Simulate Member 3 evaluating candidate slots and picking the best one."""
        candidate_slots = [
            {
                "request_id": f"OPT_{track_section}_NIGHT",
                "track_section": track_section,
                "requested_date": target_date,
                "proposed_start_time": "01:30",
                "proposed_end_time": "04:30",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": f"OPT_{track_section}_MORNING_PEAK",
                "track_section": track_section,
                "requested_date": target_date,
                "proposed_start_time": "07:00",
                "proposed_end_time": "10:00",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": f"OPT_{track_section}_AFTERNOON",
                "track_section": track_section,
                "requested_date": target_date,
                "proposed_start_time": "12:00",
                "proposed_end_time": "15:00",
                "required_duration_minutes": 180.0,
                "maintenance_priority": "HIGH",
            },
            {
                "request_id": f"OPT_{track_section}_INVALID_DURATION",
                "track_section": track_section,
                "requested_date": target_date,
                "proposed_start_time": "12:00",
                "proposed_end_time": "15:00",
                "required_duration_minutes": -50.0,  # Deliberately invalid candidate
                "maintenance_priority": "HIGH",
            },
        ]

        ranking_results = self.adapter.rank_candidate_slots(candidate_slots)
        pareto_tradeoffs = self.adapter.compute_pareto_tradeoffs(candidate_slots)

        return {
            "selected_slot_id": ranking_results["recommended_request_id"],
            "ranking_results": ranking_results,
            "pareto_tradeoffs": pareto_tradeoffs,
        }


class MockMember4SafetyValidation:
    """Simulates Member 4 receiving Member 2's conflict payload and executing interlocking checks."""

    def __init__(self):
        self.adapter = Member4ValidationAdapter()

    def certify_maintenance_block(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Member 4's safety & interlocking decision logic."""
        payload: Member4ValidationPayload = self.adapter.get_validation_payload(request)

        # Member 4 logic: certify only if conflicting trains <= 2 and risk is not CRITICAL
        is_certified = (payload.affected_train_count <= 2) and (payload.risk_category != "CRITICAL")
        certification_notes = []

        if payload.affected_train_count > 2:
            certification_notes.append(
                f"Headway conflict: {payload.affected_train_count} trains exceed single-track diversion capacity."
            )
        if payload.risk_category == "CRITICAL":
            certification_notes.append("Operational risk level is CRITICAL; requires Chief Operating Manager clearance.")

        if is_certified:
            certification_notes.append("Safety criteria satisfied. Traction power isolation permitted.")

        return {
            "request_id": payload.request_id,
            "certified_by_member4": is_certified,
            "conflicting_trains_count": payload.affected_train_count,
            "disruption_score_received": payload.maintenance_exposure_score,
            "risk_tier_received": payload.risk_category,
            "certification_notes": certification_notes,
            "disclaimer": payload.disclaimer,
        }


class MockMember5WebDashboard:
    """Simulates Member 5 calling Member 2 endpoints to render dashboard metrics."""

    @staticmethod
    def render_summary_card(prediction: Dict[str, Any]) -> Dict[str, str]:
        """Format prediction results into UI display tokens."""
        risk = prediction.get("risk_category", "UNKNOWN")
        color_map = {
            "LOW": "#28a745",       # Green
            "MEDIUM": "#ffc107",    # Yellow
            "HIGH": "#fd7e14",      # Orange
            "CRITICAL": "#dc3545",  # Red
        }

        return {
            "card_title": f"Block Request: {prediction.get('request_id')}",
            "badge_color": color_map.get(risk, "#6c757d"),
            "disruption_index": f"{prediction.get('maintenance_exposure_score', 0):.1f} / 100",
            "predicted_delay": f"{prediction.get('predicted_baseline_delay_minutes', 0):.1f} mins",
            "affected_services": f"{prediction.get('affected_train_count', 0)} trains",
            "quality_status": prediction.get("data_quality", {}).get("status", "VALID"),
        }
