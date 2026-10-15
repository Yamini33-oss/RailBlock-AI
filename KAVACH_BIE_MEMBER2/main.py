"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Master CLI Orchestrator and Pipeline Runner
===============================================================================
Executes the full end-to-end lifecycle in a single command:
1. Synthetic Data Generation (deterministic & reproducible)
2. Data Quality & Schema Validation
3. Model Training & Champion Model Selection
4. Performance Evaluation & Report Generation (JSON & Markdown)
5. Demonstration Inference for a Single Maintenance Block
6. Multi-Candidate Window Comparison & Ranking

Usage:
    python main.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    DELAYS_DATA_FILE,
    EVALUATION_REPORT_MD,
    METADATA_FILE,
    MODEL_FILE,
)
from data_loader import DataLoader
from evaluate_model import run_evaluation
from generate_data import generate_synthetic_data, save_synthetic_datasets
from predict_delay import compare_candidate_windows, predict_maintenance_window
from train_model import run_training_pipeline


def print_banner():
    banner = r"""
===============================================================================
  _  __     ___      __     _    ____ _   _   ____  ___ _____ 
 | |/ /    / \ \    / /    / \  / ___| | | | | __ )|_ _| ____|
 | ' /    / _ \ \  / /    / _ \| |   | |_| | |  _ \ | ||  _|  
 | . \   / ___ \ \/ /    / ___ \ |___|  _  | | |_) || || |___ 
 |_|\_\ /_/   \_\__/    /_/   \_\____|_| |_| |____/|___|_____|
                                                               
 Member 2: Advanced AI/ML Train Delay Prediction & Disruption Scoring
===============================================================================
"""
    print(banner)


def main():
    print_banner()

    # -------------------------------------------------------------------------
    # Step 1: Ensure Synthetic Datasets Exist
    # -------------------------------------------------------------------------
    print("\n[STEP 1/5] Ensuring Dataset Availability...")
    if not DELAYS_DATA_FILE.exists():
        print(" -> Data files missing. Generating reproducible synthetic datasets...")
        datasets = generate_synthetic_data()
        save_synthetic_datasets(datasets)
        print(" -> Synthetic datasets successfully created in ./data/")
    else:
        print(" -> Existing railway datasets found in ./data/")

    # -------------------------------------------------------------------------
    # Step 2: Validate Data Quality
    # -------------------------------------------------------------------------
    print("\n[STEP 2/5] Validating Data Integrity...")
    loader = DataLoader(auto_generate=False)
    delays_df = loader.load_delays(validate=True)
    schedules_df = loader.load_schedules(validate=True)
    traffic_df = loader.load_traffic(validate=True)
    print(f" -> Validated {len(delays_df)} historical delay records.")
    print(f" -> Validated {len(schedules_df)} timetabled train schedules.")
    print(f" -> Validated {len(traffic_df)} traffic density records.")

    # -------------------------------------------------------------------------
    # Step 3: Train Models & Select Champion Pipeline
    # -------------------------------------------------------------------------
    print("\n[STEP 3/5] Executing Model Training & Candidate Benchmarking...")
    pipeline, metadata = run_training_pipeline()
    champ_name = metadata.get("best_model_name")
    champ_mae = metadata.get("champion_metrics", {}).get("mae")
    imp_pct = metadata.get("champion_metrics", {}).get("pct_improvement_over_baseline")
    print(f" -> Champion Model Selected: {champ_name}")
    print(f" -> Hold-Out Test MAE      : {champ_mae:.2f} minutes ({imp_pct:.1f}% improvement over baseline)")

    # -------------------------------------------------------------------------
    # Step 4: Comprehensive Model Evaluation
    # -------------------------------------------------------------------------
    print("\n[STEP 4/5] Running Comprehensive Model Evaluation...")
    eval_summary = run_evaluation()
    print(f" -> JSON Report written to: {eval_summary['target_column']}")
    print(f" -> Markdown Report saved to: {EVALUATION_REPORT_MD}")

    # -------------------------------------------------------------------------
    # Step 5: Live Inference Demonstration for Member 3
    # -------------------------------------------------------------------------
    print("\n[STEP 5/5] Executing Live Inference & Candidate Ranking Demonstration...")

    candidate_request = {
        "request_id": "DEMO_REQ_NDLS_001",
        "track_section": "SEC_NDLS_CNB",
        "requested_date": "2026-10-25",
        "proposed_start_time": "01:30",
        "proposed_end_time": "04:30",
        "required_duration_minutes": 180.0,
        "maintenance_priority": "HIGH",
    }
    prediction = predict_maintenance_window(candidate_request)

    print("\n--- Single Window Prediction Demo ---")
    print(f" Request ID             : {prediction['request_id']}")
    print(f" Track Section          : {candidate_request['track_section']}")
    print(f" Time Slot              : {candidate_request['proposed_start_time']} to {candidate_request['proposed_end_time']} ({candidate_request['required_duration_minutes']} mins)")
    print(f" Predicted Baseline Delay: {prediction['predicted_baseline_delay_minutes']:.1f} minutes")
    print(f" Affected Trains Count  : {prediction['affected_train_count']} scheduled trains")
    print(f" Corridor Density       : {prediction['traffic_density']:.2f}")
    print(f" Maintenance Exposure   : {prediction['maintenance_exposure_score']:.1f} / 100")
    print(f" Operational Risk Level : {prediction['risk_category']}")
    print(f" Data Quality Status    : {prediction['data_quality']['status']}")
    print(f" Uncertainty Interval   : {prediction['uncertainty']['lower_bound_minutes']}m to {prediction['uncertainty']['upper_bound_minutes']}m (method: {prediction['uncertainty']['method']})")


    # Multi-window comparison demonstration
    print("\n--- Multi-Candidate Window Ranking Demo (for Member 3 Optimizer) ---")
    candidates = [
        {
            "request_id": "SLOT_A_NIGHT",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-25",
            "proposed_start_time": "01:30",
            "proposed_end_time": "04:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        },
        {
            "request_id": "SLOT_B_PEAK_MORNING",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-25",
            "proposed_start_time": "06:30",
            "proposed_end_time": "09:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        },
        {
            "request_id": "SLOT_C_AFTERNOON",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-25",
            "proposed_start_time": "12:00",
            "proposed_end_time": "15:00",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        },
    ]

    ranking_res = compare_candidate_windows(candidates)
    print(f" Recommended Slot: {ranking_res['recommended_request_id']}")
    for cand in ranking_res["ranked_candidates"]:
        p = cand["prediction"]
        badge = "[RECOMMENDED]" if cand["is_recommended"] else "             "
        print(
            f" {badge} Rank #{cand['rank']}: {p['request_id']} | "
            f"Score: {p['disruption_score']:<5.1f} | Delay: {p['predicted_delay_minutes']:<4.1f}m | "
            f"Trains: {p['affected_train_count']} | Risk: {p['risk_category']}"
        )


    print("\n" + "=" * 70)
    print(" [SUCCESS] KAVACH BIE Member 2 Pipeline Completed All Stages Flawlessly!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
