"""Demo runner for KAVACH BIE Member 3 AI Block Planning and Optimization Engine.

Demonstrates end-to-end block recommendation using synthetic datasets:
1. Loads train schedules, traffic density, resources, and section statuses.
2. Formulates a maintenance request for Track Section SEC-01.
3. Runs candidate window generation, evaluation, OR-Tools CP-SAT optimization, and Member 4 validation.
4. Outputs human-readable results and writes demo_input.json and demo_output.json.
"""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from optimizer.data_adapter import DataLoader
from optimizer.schemas import MaintenancePriority, MaintenanceRequest, PlanningConfig
from optimizer.service import optimize_maintenance_window

IST = ZoneInfo("Asia/Kolkata")
DATA_DIR = Path(__file__).parent / "data" / "synthetic"


def run_demo():
    print("=" * 80)
    print("  KAVACH BIE (Block Intelligence Engine) — Member 3 Core Optimization Engine")
    print("  Problem Statement: SIH26027 | Google OR-Tools CP-SAT Multi-Objective Model")
    print("=" * 80)

    # 1. Load Synthetic Datasets
    print("\n[1] Ingesting synthetic railway datasets from data/synthetic/...")
    trains = DataLoader.load_train_schedules(DATA_DIR / "train_schedule.csv")
    traffic = DataLoader.load_traffic_density(DATA_DIR / "traffic_density.csv")
    resources = DataLoader.load_resource_availability(DATA_DIR / "resource_availability.csv")
    sections = DataLoader.load_section_availability(DATA_DIR / "section_availability.csv")

    print(f"    - Loaded {len(trains)} scheduled train movements.")
    print(f"    - Loaded {len(traffic)} section traffic density records.")
    print(f"    - Loaded {len(resources)} resource availability intervals.")
    print(f"    - Loaded {len(sections)} section availability records.")

    # 2. Formulate Maintenance Request
    print("\n[2] Formulating Maintenance Request (MR-DEMO-001)...")
    req = MaintenanceRequest(
        request_id="MR-DEMO-001",
        track_section_id="SEC-01",
        planning_start=datetime(2026, 10, 15, 8, 0, tzinfo=IST),
        planning_end=datetime(2026, 10, 15, 18, 0, tzinfo=IST),
        required_duration_minutes=60,
        maintenance_priority=MaintenancePriority.HIGH,
        required_resources=["TRACK_TEAM_A"],
        earliest_start_time=datetime(2026, 10, 15, 9, 0, tzinfo=IST),
        latest_end_time=datetime(2026, 10, 15, 17, 0, tzinfo=IST),
    )

    # Save demo_input.json
    input_payload = {
        "request_id": req.request_id,
        "track_section_id": req.track_section_id,
        "planning_start": req.planning_start.isoformat(),
        "planning_end": req.planning_end.isoformat(),
        "required_duration_minutes": req.required_duration_minutes,
        "maintenance_priority": req.maintenance_priority.value,
        "required_resources": req.required_resources,
        "earliest_start_time": req.earliest_start_time.isoformat() if req.earliest_start_time else None,
        "latest_end_time": req.latest_end_time.isoformat() if req.latest_end_time else None,
    }
    with open(Path(__file__).parent / "demo_input.json", "w", encoding="utf-8") as f:
        json.dump(input_payload, f, indent=2)
    print("    - Saved request parameters to demo_input.json.")

    # 3. Execute Optimization
    print("\n[3] Executing OR-Tools CP-SAT Optimization and Validation Loop...")
    config = PlanningConfig(
        step_minutes=15,
        max_validation_attempts=5,
        solver_time_limit_seconds=10.0,
        max_alternatives=4,
    )
    response = optimize_maintenance_window(
        request=req,
        input_data={
            "train_data": trains,
            "traffic_data": traffic,
            "resource_data": resources,
            "section_data": sections,
        },
        config=config,
    )

    # Save demo_output.json
    output_dict = response.model_dump(mode="json")
    with open(Path(__file__).parent / "demo_output.json", "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2)
    print("    - Saved structured response to demo_output.json.")

    # 4. Display Results
    print("\n" + "=" * 80)
    print("  OPTIMIZATION SUMMARY & RECOMMENDATION")
    print("=" * 80)
    print(f"Status:               {response.status.value}")
    print(f"Request ID:           {response.request_id}")
    if response.recommendation:
        print(f"Section:              {response.recommendation.track_section_id}")
        print(f"Recommended Start:    {response.recommendation.start_time}")
        print(f"Recommended End:      {response.recommendation.end_time}")
        print(f"Duration:             {response.recommendation.duration_minutes} minutes")
    if response.estimated_impact:
        print(f"Affected Trains:      {response.estimated_impact.affected_train_count}")
        print(f"Predicted Delay:      {response.estimated_impact.predicted_delay_minutes} minutes")
        print(f"Traffic Density:      {response.estimated_impact.traffic_density}")
    if response.solver:
        print(f"Solver Status:        {response.solver.status.value} (Optimal: {response.solver.is_optimal})")
        print(f"Objective Score:      {response.solver.objective_score}")
        print(f"Solver Wall Time:     {response.solver.wall_time_seconds}s")
    if response.validation:
        print(f"Member 4 Validation:  {response.validation.status.value} ({response.validation.reason})")
        print(f"Validation Attempts:  {response.validation.validation_attempts}")

    print("\nDecision Explanations:")
    for idx, exp in enumerate(response.explanation, 1):
        print(f"  {idx}. {exp}")

    if response.alternatives:
        print("\nRanked Alternative Windows:")
        for alt in response.alternatives:
            print(
                f"  Rank #{alt.rank} [{alt.candidate_id}]: {alt.start_time.strftime('%H:%M')} - "
                f"{alt.end_time.strftime('%H:%M')} (Score: {alt.objective_score:.4f}, "
                f"Affected Trains: {alt.affected_train_count}, "
                f"Predicted Delay: {alt.predicted_delay_minutes:.1f}m)"
            )
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
