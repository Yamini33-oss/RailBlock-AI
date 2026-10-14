"""Google OR-Tools CP-SAT constraint-based optimization engine for KAVACH BIE Member 3.

Implements mathematical modeling of maintenance block scheduling using CP-SAT.
Enforces hard constraints (feasibility, horizons, resources, non-overlapping section usage)
and optimizes a multi-objective cost function to recommend the best feasible schedule.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    cp_model = None
    ORTOOLS_AVAILABLE = False

from optimizer.exceptions import DependencyMissingError, SolverError
from optimizer.schemas import (
    CandidateEvaluation,
    PlanningConfig,
    SolverMetadata,
    SolverStatus,
)

logger = logging.getLogger(__name__)


class SolverResult:
    """Internal container for CP-SAT solve results."""

    def __init__(
        self,
        status: SolverStatus,
        selected_candidate_id: Optional[str] = None,
        ranked_candidate_ids: Optional[List[str]] = None,
        objective_value: Optional[float] = None,
        wall_time_seconds: float = 0.0,
        is_optimal: bool = False,
        details: Optional[Dict[str, str]] = None,
    ) -> None:
        self.status = status
        self.selected_candidate_id = selected_candidate_id
        self.ranked_candidate_ids = ranked_candidate_ids or []
        self.objective_value = objective_value
        self.wall_time_seconds = wall_time_seconds
        self.is_optimal = is_optimal
        self.details = details or {}

    def to_metadata(self) -> SolverMetadata:
        return SolverMetadata(
            status=self.status,
            objective_score=self.objective_value,
            wall_time_seconds=round(self.wall_time_seconds, 4),
            is_optimal=self.is_optimal,
        )


class OrToolsBlockOptimizer:
    """Constraint programming optimizer for railway maintenance blocks using OR-Tools CP-SAT."""

    def __init__(self, config: Optional[PlanningConfig] = None) -> None:
        if not ORTOOLS_AVAILABLE:
            raise DependencyMissingError(
                "Google OR-Tools is not installed. Please install it using: "
                "pip install ortools>=9.10.0"
            )
        self.config = config or PlanningConfig()

    def solve_single_request(
        self,
        evaluations: List[CandidateEvaluation],
    ) -> SolverResult:
        """Solve single-request candidate window selection using CP-SAT.

        Args:
            evaluations: List of evaluated candidate windows.

        Returns:
            SolverResult containing chosen candidate, ranking, and solver metadata.
        """
        start_time = time.perf_counter()

        if not evaluations:
            return SolverResult(
                status=SolverStatus.INFEASIBLE,
                wall_time_seconds=time.perf_counter() - start_time,
                details={"reason": "No candidate evaluations supplied to solver."},
            )

        model = cp_model.CpModel()
        num_candidates = len(evaluations)

        # 1. Decision Variables: x_i in {0, 1} for each candidate window
        x: Dict[int, cp_model.IntVar] = {}
        for i, eval_cand in enumerate(evaluations):
            x[i] = model.NewBoolVar(f"x_cand_{eval_cand.candidate_id}")

        # 2. Hard Constraints
        feasible_indices: List[int] = []
        for i, eval_cand in enumerate(evaluations):
            if not eval_cand.is_feasible:
                # Infeasible candidate must never be chosen
                model.Add(x[i] == 0)
            else:
                feasible_indices.append(i)

        if not feasible_indices:
            # All candidates violate hard constraints
            wall_time = time.perf_counter() - start_time
            logger.info("All %d candidates are infeasible. Solver returns INFEASIBLE.", num_candidates)
            return SolverResult(
                status=SolverStatus.INFEASIBLE,
                wall_time_seconds=wall_time,
                details={"reason": "All generated candidates violate hard operational constraints."},
            )

        # Exactly one feasible candidate must be selected
        model.Add(sum(x[i] for i in feasible_indices) == 1)

        # 3. Objective Function (Integer-scaled cost minimization)
        # Cost factor: round(score * 10,000) for integer CP-SAT representation
        SCALE = 10_000
        costs: List[Tuple[cp_model.IntVar, int]] = []
        for i in feasible_indices:
            int_cost = int(round(evaluations[i].objective_score * SCALE))
            costs.append((x[i], int_cost))

        model.Minimize(sum(var * cost for var, cost in costs))

        # 4. Solver Configuration
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.solver_time_limit_seconds
        solver.parameters.random_seed = 42
        solver.parameters.num_search_workers = 1  # Deterministic execution

        status = solver.Solve(model)
        wall_time = time.perf_counter() - start_time

        if status == cp_model.OPTIMAL:
            solver_status = SolverStatus.OPTIMAL
            is_optimal = True
        elif status == cp_model.FEASIBLE:
            solver_status = SolverStatus.FEASIBLE
            is_optimal = False
        elif status == cp_model.INFEASIBLE:
            return SolverResult(
                status=SolverStatus.INFEASIBLE,
                wall_time_seconds=wall_time,
                details={"reason": "CP-SAT proved the model is infeasible."},
            )
        elif status == cp_model.MODEL_INVALID:
            raise SolverError("CP-SAT model formulation is invalid.")
        else:
            return SolverResult(
                status=SolverStatus.TIMEOUT,
                wall_time_seconds=wall_time,
                details={"reason": "Solver reached time limit without finding a solution."},
            )

        # 5. Extract Selected Candidate
        selected_id = None
        for i in feasible_indices:
            if solver.Value(x[i]) == 1:
                selected_id = evaluations[i].candidate_id
                break

        # 6. Rank all feasible candidates by objective score
        feasible_evals = [evaluations[i] for i in feasible_indices]
        ranked_evals = sorted(feasible_evals, key=lambda e: e.objective_score)
        ranked_ids = [e.candidate_id for e in ranked_evals]

        obj_val = solver.ObjectiveValue() / SCALE

        logger.info(
            "CP-SAT solved in %.4fs (status=%s, optimal=%s, selected=%s, obj=%.4f)",
            wall_time,
            solver_status.value,
            is_optimal,
            selected_id,
            obj_val,
        )

        return SolverResult(
            status=solver_status,
            selected_candidate_id=selected_id,
            ranked_candidate_ids=ranked_ids,
            objective_value=round(obj_val, 4),
            wall_time_seconds=wall_time,
            is_optimal=is_optimal,
        )

    def solve_joint_requests(
        self,
        request_evaluations: Dict[str, List[CandidateEvaluation]],
    ) -> Dict[str, SolverResult]:
        """Solve joint maintenance scheduling for multiple requests.

        Enforces non-overlapping block intervals on the same track section.
        """
        start_time = time.perf_counter()
        model = cp_model.CpModel()
        SCALE = 10_000

        x_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        eval_lookup: Dict[Tuple[str, str], CandidateEvaluation] = {}
        feasible_per_req: Dict[str, List[str]] = {}

        for req_id, evals in request_evaluations.items():
            feasible_per_req[req_id] = []
            for ev in evals:
                var = model.NewBoolVar(f"x_{req_id}_{ev.candidate_id}")
                x_vars[(req_id, ev.candidate_id)] = var
                eval_lookup[(req_id, ev.candidate_id)] = ev
                if not ev.is_feasible:
                    model.Add(var == 0)
                else:
                    feasible_per_req[req_id].append(ev.candidate_id)

            if not feasible_per_req[req_id]:
                # If any request has zero feasible candidates, joint model is infeasible
                return {
                    r_id: SolverResult(
                        status=SolverStatus.INFEASIBLE,
                        wall_time_seconds=time.perf_counter() - start_time,
                        details={"reason": f"Request {req_id} has zero feasible candidates."},
                    )
                    for r_id in request_evaluations
                }

            # Exactly one candidate per request
            model.Add(sum(x_vars[(req_id, c_id)] for c_id in feasible_per_req[req_id]) == 1)

        # Section Conflict Constraints (No two blocks on the same section may overlap)
        req_list = list(request_evaluations.keys())
        for i in range(len(req_list)):
            for j in range(i + 1, len(req_list)):
                r1 = req_list[i]
                r2 = req_list[j]
                for c1_id in feasible_per_req[r1]:
                    for c2_id in feasible_per_req[r2]:
                        ev1 = eval_lookup[(r1, c1_id)]
                        ev2 = eval_lookup[(r2, c2_id)]
                        if ev1.track_section_id == ev2.track_section_id:
                            # Check overlap
                            if max(ev1.start_time, ev2.start_time) < min(ev1.end_time, ev2.end_time):
                                # Cannot both be 1
                                model.Add(x_vars[(r1, c1_id)] + x_vars[(r2, c2_id)] <= 1)

        # Objective: minimize sum of scores
        total_costs = []
        for (r_id, c_id), var in x_vars.items():
            ev = eval_lookup[(r_id, c_id)]
            int_cost = int(round(ev.objective_score * SCALE))
            total_costs.append(var * int_cost)

        model.Minimize(sum(total_costs))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.solver_time_limit_seconds
        solver.parameters.random_seed = 42

        status = solver.Solve(model)
        wall_time = time.perf_counter() - start_time

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {
                r_id: SolverResult(
                    status=SolverStatus.INFEASIBLE,
                    wall_time_seconds=wall_time,
                    details={"reason": "No joint feasible schedule without section conflicts."},
                )
                for r_id in request_evaluations
            }

        solver_status = SolverStatus.OPTIMAL if status == cp_model.OPTIMAL else SolverStatus.FEASIBLE
        is_optimal = (status == cp_model.OPTIMAL)

        results: Dict[str, SolverResult] = {}
        for r_id, evals in request_evaluations.items():
            sel_id = None
            for c_id in feasible_per_req[r_id]:
                if solver.Value(x_vars[(r_id, c_id)]) == 1:
                    sel_id = c_id
                    break
            ranked = sorted(
                [eval_lookup[(r_id, c_id)] for c_id in feasible_per_req[r_id]],
                key=lambda e: e.objective_score,
            )
            results[r_id] = SolverResult(
                status=solver_status,
                selected_candidate_id=sel_id,
                ranked_candidate_ids=[e.candidate_id for e in ranked],
                objective_value=eval_lookup[(r_id, sel_id)].objective_score if sel_id else None,
                wall_time_seconds=wall_time,
                is_optimal=is_optimal,
            )

        return results
