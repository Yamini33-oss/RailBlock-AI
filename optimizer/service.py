"""Main orchestration service for KAVACH BIE Member 3 Optimization Engine.

Provides the complete end-to-end workflow:
1. Validates maintenance requests.
2. Generates candidate maintenance windows.
3. Evaluates impact, traffic, train movements, and predictions.
4. Solves constraint optimization via Google OR-Tools CP-SAT.
5. Performs interactive validation with Member 4 conflict validator.
6. Formulates transparent human-readable explanations and rankings.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from optimizer.candidate_evaluator import evaluate_candidate
from optimizer.candidate_generator import generate_candidate_windows
from optimizer.data_adapter import (
    BaselineDelayPredictor,
    DataLoader,
    DelayPredictorInterface,
    Member2PredictorAdapter,
)
from optimizer.exceptions import (
    InvalidRequestError,
    NoFeasibleWindowError,
    PredictionServiceError,
    ValidationServiceError,
)
from optimizer.objective import ObjectiveCalculator
from optimizer.optimizer_engine import OrToolsBlockOptimizer
from optimizer.schemas import (
    AlternativeWindow,
    CandidateEvaluation,
    CandidateWindow,
    ImpactSummary,
    MaintenanceRequest,
    ObjectiveWeights,
    OptimizationResponse,
    OptimizationStatus,
    PlanningConfig,
    RecommendationDetail,
    RejectedCandidateSummary,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    SolverMetadata,
    SolverStatus,
    TrafficDensityRecord,
    TrainSchedule,
    ValidationResult,
    ValidationStatus,
    ValidationSummary,
)
from optimizer.validation_client import (
    ConflictValidationInterface,
    MockMember4Validator,
)

logger = logging.getLogger(__name__)


def validate_maintenance_request(request: Union[MaintenanceRequest, Dict[str, Any]]) -> MaintenanceRequest:
    """Validate maintenance request inputs against domain and schema rules."""
    if isinstance(request, dict):
        try:
            return MaintenanceRequest(**request)
        except Exception as exc:
            raise InvalidRequestError(f"Maintenance request validation failed: {exc}", details={"raw": str(request)}) from exc
    elif isinstance(request, MaintenanceRequest):
        return request
    else:
        raise InvalidRequestError(f"Unsupported request type: {type(request)}")


def validate_recommendation_with_member4(
    recommendation: CandidateEvaluation,
    validator: Optional[ConflictValidationInterface] = None,
) -> ValidationResult:
    """Submit candidate recommendation to Member 4 for operational validation."""
    if validator is None:
        validator = MockMember4Validator()
    return validator.validate_candidate(recommendation)


def get_ranked_alternatives(result: OptimizationResponse) -> List[AlternativeWindow]:
    """Retrieve alternative candidate windows from an optimization response."""
    return result.alternatives


def explain_recommendation(result: OptimizationResponse) -> List[str]:
    """Retrieve human-readable explanations from an optimization response."""
    return result.explanation


def optimize_maintenance_window(
    request: Union[MaintenanceRequest, Dict[str, Any]],
    input_data: Optional[Dict[str, Any]] = None,
    config: Optional[PlanningConfig] = None,
    predictor: Optional[DelayPredictorInterface] = None,
    validator: Optional[ConflictValidationInterface] = None,
) -> OptimizationResponse:
    """End-to-end orchestration of maintenance block planning and optimization.

    Args:
        request: Validated MaintenanceRequest or dict.
        input_data: Dict containing lists or file paths for 'train_data', 'traffic_data',
                    'resource_data', 'section_data'.
        config: Runtime configuration options.
        predictor: Delay prediction service (defaults to BaselineDelayPredictor).
        validator: Member 4 conflict validator (defaults to MockMember4Validator).

    Returns:
        Structured OptimizationResponse complying with Member 5 API contract.
    """
    if config is None:
        config = PlanningConfig()

    input_data = input_data or {}
    req_id = "UNKNOWN"

    # Step 1: Validate Maintenance Request
    try:
        validated_request = validate_maintenance_request(request)
        req_id = validated_request.request_id
    except InvalidRequestError as exc:
        logger.error("Invalid maintenance request: %s", exc)
        return OptimizationResponse(
            status=OptimizationStatus.INVALID_REQUEST,
            request_id=req_id,
            explanation=[f"Request rejected: {exc.message}"],
        )
    except Exception as exc:
        logger.error("Unexpected error validating request: %s", exc)
        return OptimizationResponse(
            status=OptimizationStatus.INVALID_REQUEST,
            request_id=req_id,
            explanation=[f"Unexpected request format: {exc}"],
        )

    # Step 2: Prepare Input Data
    try:
        raw_trains = input_data.get("train_data", [])
        train_data: List[TrainSchedule] = (
            DataLoader.load_train_schedules(raw_trains)
            if not (raw_trains and isinstance(raw_trains[0], TrainSchedule))
            else raw_trains
        )

        raw_traffic = input_data.get("traffic_data", [])
        traffic_data: List[TrafficDensityRecord] = (
            DataLoader.load_traffic_density(raw_traffic)
            if not (raw_traffic and isinstance(raw_traffic[0], TrafficDensityRecord))
            else raw_traffic
        )

        raw_resources = input_data.get("resource_data", [])
        resource_data: List[ResourceAvailabilityRecord] = (
            DataLoader.load_resource_availability(raw_resources)
            if not (raw_resources and isinstance(raw_resources[0], ResourceAvailabilityRecord))
            else raw_resources
        )

        raw_sections = input_data.get("section_data", [])
        section_data: List[SectionAvailabilityRecord] = (
            DataLoader.load_section_availability(raw_sections)
            if not (raw_sections and isinstance(raw_sections[0], SectionAvailabilityRecord))
            else raw_sections
        )
    except Exception as exc:
        logger.error("Failed to parse input datasets: %s", exc)
        return OptimizationResponse(
            status=OptimizationStatus.INVALID_REQUEST,
            request_id=req_id,
            explanation=[f"Dataset formatting error: {exc}"],
        )

    if predictor is None:
        predictor = BaselineDelayPredictor()

    if validator is None:
        validator = MockMember4Validator()

    # Step 3: Candidate Window Generation
    try:
        candidate_windows = generate_candidate_windows(validated_request, config)
    except InvalidRequestError as exc:
        return OptimizationResponse(
            status=OptimizationStatus.INVALID_REQUEST,
            request_id=req_id,
            explanation=[f"Candidate generation rejected: {exc.message}"],
        )

    if not candidate_windows:
        msg = (
            f"No candidate windows could be generated within planning horizon "
            f"({validated_request.planning_start.strftime('%Y-%m-%d %H:%M')} to "
            f"{validated_request.planning_end.strftime('%Y-%m-%d %H:%M')}) for duration "
            f"{validated_request.required_duration_minutes} minutes."
        )
        logger.warning(msg)
        return OptimizationResponse(
            status=OptimizationStatus.NO_FEASIBLE_WINDOW,
            request_id=req_id,
            explanation=[msg],
        )

    # Step 4: Evaluate Candidate Windows
    calculator = ObjectiveCalculator(config.weights)
    evaluations: List[CandidateEvaluation] = []
    rejected_summaries: List[RejectedCandidateSummary] = []

    try:
        for cand in candidate_windows:
            cand_eval = evaluate_candidate(
                candidate=cand,
                request=validated_request,
                train_data=train_data,
                traffic_data=traffic_data,
                prediction_service=predictor,
                resource_data=resource_data,
                section_data=section_data,
                calculator=calculator,
            )
            evaluations.append(cand_eval)
            if not cand_eval.is_feasible:
                rejected_summaries.append(
                    RejectedCandidateSummary(
                        candidate_id=cand.candidate_id,
                        start_time=cand.start_time,
                        end_time=cand.end_time,
                        reasons=cand_eval.hard_violations,
                    )
                )
    except PredictionServiceError as exc:
        logger.error("Prediction service unavailable or failed: %s", exc)
        return OptimizationResponse(
            status=OptimizationStatus.PREDICTION_UNAVAILABLE,
            request_id=req_id,
            explanation=[f"Delay prediction service failed: {exc.message}"],
        )
    except Exception as exc:
        logger.error("Error during candidate evaluation: %s", exc)
        return OptimizationResponse(
            status=OptimizationStatus.OPTIMIZATION_ERROR,
            request_id=req_id,
            explanation=[f"Evaluation error: {exc}"],
        )

    # Step 5: Constraint-Based Optimization via Google OR-Tools CP-SAT
    try:
        optimizer_engine = OrToolsBlockOptimizer(config)
        solve_result = optimizer_engine.solve_single_request(evaluations)
    except Exception as exc:
        logger.error("CP-SAT solver failed: %s", exc)
        return OptimizationResponse(
            status=OptimizationStatus.OPTIMIZATION_ERROR,
            request_id=req_id,
            explanation=[f"OR-Tools solver execution failed: {exc}"],
        )

    if solve_result.status == SolverStatus.INFEASIBLE or not solve_result.selected_candidate_id:
        return OptimizationResponse(
            status=OptimizationStatus.NO_FEASIBLE_WINDOW,
            request_id=req_id,
            solver=solve_result.to_metadata(),
            rejected_candidates=rejected_summaries,
            explanation=[
                "All candidate maintenance windows violate hard operational constraints.",
                f"Generated {len(candidate_windows)} candidates; all {len(rejected_summaries)} violated constraints.",
            ],
        )

    # Step 6: Conflict Validation Loop with Member 4
    eval_by_id = {e.candidate_id: e for e in evaluations}
    ranked_feasible_ids = solve_result.ranked_candidate_ids

    selected_eval: Optional[CandidateEvaluation] = None
    validation_res: Optional[ValidationResult] = None
    validation_attempts = 0
    validation_history: List[str] = []

    for cand_id in ranked_feasible_ids:
        if validation_attempts >= config.max_validation_attempts:
            logger.warning("Reached maximum validation attempts (%d).", config.max_validation_attempts)
            break

        cand_eval = eval_by_id[cand_id]
        validation_attempts += 1

        try:
            val_out = validate_recommendation_with_member4(cand_eval, validator)
        except ValidationServiceError as exc:
            logger.error("Member 4 validation service error: %s", exc)
            return OptimizationResponse(
                status=OptimizationStatus.VALIDATION_ERROR,
                request_id=req_id,
                explanation=[f"Validation service communication error: {exc.message}"],
            )
        except Exception as exc:
            logger.error("Unexpected error calling Member 4 validator: %s", exc)
            return OptimizationResponse(
                status=OptimizationStatus.VALIDATION_ERROR,
                request_id=req_id,
                explanation=[f"Validation error: {exc}"],
            )

        if val_out.status == ValidationStatus.VALID:
            selected_eval = cand_eval
            validation_res = val_out
            validation_history.append(
                f"Candidate {cand_id} ({cand_eval.start_time.strftime('%H:%M')}-{cand_eval.end_time.strftime('%H:%M')}) passed operational validation."
            )
            break
        elif val_out.status == ValidationStatus.CONFLICT:
            reason = val_out.reason or "Headway or interlocking conflict"
            validation_history.append(
                f"Candidate {cand_id} was rejected by Member 4 conflict validator: {reason}."
            )
            rejected_summaries.append(
                RejectedCandidateSummary(
                    candidate_id=cand_id,
                    start_time=cand_eval.start_time,
                    end_time=cand_eval.end_time,
                    reasons=[f"Member 4 Conflict: {reason}"],
                )
            )
            continue
        elif val_out.status == ValidationStatus.VALIDATION_UNAVAILABLE:
            if config.allow_unvalidated_fallback:
                selected_eval = cand_eval
                validation_res = val_out
                validation_history.append(
                    f"Member 4 validation unavailable; accepted candidate {cand_id} under provisional fallback."
                )
                break
            else:
                return OptimizationResponse(
                    status=OptimizationStatus.VALIDATION_UNAVAILABLE,
                    request_id=req_id,
                    explanation=[
                        "Member 4 conflict detection service is unavailable.",
                        val_out.reason or "Validator connection refused.",
                    ],
                )
        else:
            return OptimizationResponse(
                status=OptimizationStatus.VALIDATION_ERROR,
                request_id=req_id,
                explanation=[val_out.reason or "Unknown validation status received."],
            )

    # If no candidate passed validation
    if selected_eval is None or validation_res is None or validation_res.status not in (ValidationStatus.VALID, ValidationStatus.VALIDATION_UNAVAILABLE):
        return OptimizationResponse(
            status=OptimizationStatus.NO_FEASIBLE_WINDOW,
            request_id=req_id,
            solver=solve_result.to_metadata(),
            rejected_candidates=rejected_summaries,
            explanation=[
                "No candidate maintenance window passed Member 4 operational conflict validation.",
                *validation_history,
            ],
        )

    # Step 7: Format Successful Recommendation & Alternatives
    alternatives: List[AlternativeWindow] = []
    rank_idx = 1
    for cand_id in ranked_feasible_ids:
        if cand_id != selected_eval.candidate_id and len(alternatives) < config.max_alternatives:
            ev = eval_by_id[cand_id]
            alternatives.append(
                AlternativeWindow(
                    rank=rank_idx,
                    candidate_id=ev.candidate_id,
                    start_time=ev.start_time,
                    end_time=ev.end_time,
                    duration_minutes=ev.duration_minutes,
                    objective_score=ev.objective_score,
                    affected_train_count=ev.affected_train_count,
                    predicted_delay_minutes=ev.predicted_delay_minutes,
                    traffic_density=ev.traffic_density_score,
                    validation_status=ValidationStatus.VALIDATION_PENDING,
                )
            )
            rank_idx += 1

    # Formulate clear explanations
    explanation_bullets: List[str] = [
        (
            f"Recommended maintenance block on section {selected_eval.track_section_id} from "
            f"{selected_eval.start_time.strftime('%Y-%m-%d %H:%M')} to "
            f"{selected_eval.end_time.strftime('%Y-%m-%d %H:%M')} "
            f"({selected_eval.duration_minutes} minutes)."
        ),
        (
            f"Optimization score is {selected_eval.objective_score:.4f} "
            f"(predicted disruption delay: {selected_eval.predicted_delay_minutes:.1f} mins, "
            f"affected trains: {selected_eval.affected_train_count}, "
            f"traffic density: {selected_eval.traffic_density_score:.2f})."
        ),
        *validation_history,
    ]

    if solve_result.is_optimal:
        explanation_bullets.append(
            f"Solution mathematically proven OPTIMAL by Google OR-Tools CP-SAT in {solve_result.wall_time_seconds:.3f}s."
        )
    else:
        explanation_bullets.append(
            f"Feasible schedule found by Google OR-Tools CP-SAT in {solve_result.wall_time_seconds:.3f}s."
        )

    response = OptimizationResponse(
        status=OptimizationStatus.RECOMMENDED,
        request_id=req_id,
        recommendation=RecommendationDetail(
            track_section_id=selected_eval.track_section_id,
            start_time=selected_eval.start_time,
            end_time=selected_eval.end_time,
            duration_minutes=selected_eval.duration_minutes,
        ),
        estimated_impact=ImpactSummary(
            affected_train_count=selected_eval.affected_train_count,
            predicted_delay_minutes=selected_eval.predicted_delay_minutes,
            traffic_density=selected_eval.traffic_density_score,
            affected_trains=selected_eval.affected_trains,
        ),
        validation=ValidationSummary(
            status=validation_res.status,
            reason=validation_res.reason,
            validator_used=validation_res.validator_name,
            validation_attempts=validation_attempts,
        ),
        alternatives=alternatives,
        rejected_candidates=rejected_summaries[:10],
        explanation=explanation_bullets,
        solver=solve_result.to_metadata(),
    )

    return response
