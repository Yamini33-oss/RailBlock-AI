"""Tests for Google OR-Tools CP-SAT optimizer engine."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from optimizer.optimizer_engine import OrToolsBlockOptimizer
from optimizer.schemas import (
    CandidateEvaluation,
    PlanningConfig,
    SolverStatus,
)

IST = ZoneInfo("Asia/Kolkata")


def make_eval(
    cand_id: str,
    start_h: int,
    end_h: int,
    score: float,
    feasible: bool = True,
    section: str = "SEC-01",
) -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate_id=cand_id,
        track_section_id=section,
        start_time=datetime(2026, 10, 15, start_h, 0, tzinfo=IST),
        end_time=datetime(2026, 10, 15, end_h, 0, tzinfo=IST),
        duration_minutes=(end_h - start_h) * 60,
        is_feasible=feasible,
        objective_score=score,
        hard_violations=[] if feasible else ["Hard violation"],
    )


def test_cpsat_selects_minimum_cost_feasible_candidate():
    # 3 candidates:
    # CW-01: score 0.65 (feasible)
    # CW-02: score 0.20 (feasible, lowest cost)
    # CW-03: score 0.10 (infeasible)
    evals = [
        make_eval("CW-01", 8, 9, 0.65, feasible=True),
        make_eval("CW-02", 11, 12, 0.20, feasible=True),
        make_eval("CW-03", 13, 14, 0.10, feasible=False),
    ]

    optimizer = OrToolsBlockOptimizer(PlanningConfig())
    res = optimizer.solve_single_request(evals)

    assert res.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
    assert res.selected_candidate_id == "CW-02"
    assert res.is_optimal is True
    # CW-03 must NOT be in ranked feasible candidates
    assert "CW-03" not in res.ranked_candidate_ids
    assert res.ranked_candidate_ids == ["CW-02", "CW-01"]


def test_cpsat_all_infeasible_returns_infeasible():
    evals = [
        make_eval("CW-01", 8, 9, 0.50, feasible=False),
        make_eval("CW-02", 9, 10, 0.30, feasible=False),
    ]

    optimizer = OrToolsBlockOptimizer(PlanningConfig())
    res = optimizer.solve_single_request(evals)

    assert res.status == SolverStatus.INFEASIBLE
    assert res.selected_candidate_id is None
    assert len(res.ranked_candidate_ids) == 0


def test_cpsat_joint_requests_enforces_no_section_overlap():
    # Two requests on the SAME section SEC-01
    # Req 1 has windows: 10:00-11:00 (score 0.1) and 11:00-12:00 (score 0.5)
    # Req 2 has windows: 10:00-11:00 (score 0.1) and 12:00-13:00 (score 0.4)
    # If unconstrained, both would greedily pick 10:00-11:00!
    # CP-SAT joint model must ensure their chosen intervals do not overlap.
    req1_evals = [
        make_eval("R1-CW1", 10, 11, 0.10, section="SEC-01"),
        make_eval("R1-CW2", 11, 12, 0.50, section="SEC-01"),
    ]
    req2_evals = [
        make_eval("R2-CW1", 10, 11, 0.10, section="SEC-01"),
        make_eval("R2-CW2", 12, 13, 0.40, section="SEC-01"),
    ]

    optimizer = OrToolsBlockOptimizer(PlanningConfig())
    results = optimizer.solve_joint_requests({
        "REQ-01": req1_evals,
        "REQ-02": req2_evals,
    })

    assert results["REQ-01"].status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
    assert results["REQ-02"].status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    sel1 = results["REQ-01"].selected_candidate_id
    sel2 = results["REQ-02"].selected_candidate_id

    # They cannot both be 10:00-11:00!
    assert not (sel1 == "R1-CW1" and sel2 == "R2-CW1")
    # Total combined cost is minimized: (0.10 + 0.40 = 0.50)
    assert sel1 == "R1-CW1"
    assert sel2 == "R2-CW2"
