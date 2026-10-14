"""KAVACH BIE — Member 3: AI Block Planning and Optimization Engine.

Core algorithmic component for Railway Maintenance Block Scheduling under SIH26027.
Utilizes Google OR-Tools CP-SAT for multi-criteria constraint-based optimization.
"""

__version__ = "1.0.0"
__member__ = "Member 3 — AI Block Planning and Optimization"

from optimizer.schemas import (
    MaintenanceRequest,
    MaintenancePriority,
    OptimizationStatus,
    SolverStatus,
    ValidationStatus,
    PlanningConfig,
    CandidateWindow,
    CandidateEvaluation,
    OptimizationResponse,
    AlternativeWindow,
    ImpactSummary,
    RecommendationDetail,
    ValidationSummary,
    SolverMetadata,
)
from optimizer.service import (
    optimize_maintenance_window,
    validate_maintenance_request,
    generate_candidate_windows,
    evaluate_candidate,
    validate_recommendation_with_member4,
    get_ranked_alternatives,
    explain_recommendation,
)

__all__ = [
    "MaintenanceRequest",
    "MaintenancePriority",
    "OptimizationStatus",
    "SolverStatus",
    "ValidationStatus",
    "PlanningConfig",
    "CandidateWindow",
    "CandidateEvaluation",
    "OptimizationResponse",
    "AlternativeWindow",
    "ImpactSummary",
    "RecommendationDetail",
    "ValidationSummary",
    "SolverMetadata",
    "optimize_maintenance_window",
    "validate_maintenance_request",
    "generate_candidate_windows",
    "evaluate_candidate",
    "validate_recommendation_with_member4",
    "get_ranked_alternatives",
    "explain_recommendation",
]
