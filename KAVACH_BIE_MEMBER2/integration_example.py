"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Comprehensive Cross-Module Integration Walkthrough (v1.1.0)
===============================================================================
Demonstrates the integration contracts between Member 2 and all four team members:
1. Member 1 Adapter: Ingest raw external data, harmonize columns, and audit quality.
2. Member 2 Engine: Single maintenance window prediction with data quality flags.
3. Member 3 Optimizer: Candidate comparison ranking, Pareto tradeoffs, and infeasible slot retention.
4. Member 4 Validator: Conflict handoff payload with conflicting train details and safety disclaimers.
5. Member 5 Dashboard: UI metric token rendering and risk badges.
6. Error & OOD Handling: Rejecting impossible requests and reporting OOD telemetry.

Can be run directly:
    python integration_example.py
"""

import json
import pandas as pd

from adapters.member1_adapter import Member1DataAdapter
from adapters.member3_adapter import Member3OptimizationAdapter
from adapters.member4_adapter import Member4ValidationAdapter
from adapters.mocks import (
    MockMember1DataIngestion,
    MockMember3OptimizationEngine,
    MockMember4SafetyValidation,
    MockMember5WebDashboard,
)
from predict_delay import compare_candidate_windows, predict_maintenance_window


def demonstrate_member1_integration():
    print("\n" + "=" * 75)
    print("STEP 1: Member 1 Data Ingestion, Harmonization & Quality Audit")
    print("=" * 75)

    # Simulate Member 1 providing raw unharmonized data
    raw_df = MockMember1DataIngestion.get_raw_external_delays_dataframe()
    print(f"[*] Raw Columns received from Member 1: {list(raw_df.columns)}")

    adapter = Member1DataAdapter()
    clean_df, res = adapter.harmonize_and_validate_delays(raw_df)

    print(f"[+] Harmonized Columns in Member 2 schema: {list(clean_df.columns)}")
    print(f"    - Records Validated : {len(clean_df)}")
    print(f"    - Duplicates Dropped: {res.rows_rejected}")
    print(f"    - Validation Status : {'PASSED' if res.is_valid else 'FAILED'}")

    audit = adapter.audit_incoming_batch(delays_df=clean_df)
    print(f"[+] Data Quality Summary for Delays: {json.dumps(audit['delays'], indent=2)}")


def demonstrate_single_window_prediction():
    print("\n" + "=" * 75)
    print("STEP 2: Member 2 Single Window Delay Prediction & Disruption Scoring")
    print("=" * 75)

    candidate_request = {
        "request_id": "REQ_NDLS_001A",
        "track_section": "SEC_NDLS_CNB",
        "requested_date": "2026-10-25",
        "proposed_start_time": "01:30",
        "proposed_end_time": "04:30",
        "required_duration_minutes": 180.0,
        "maintenance_priority": "HIGH",
        "traffic_density": 0.52,
    }

    result = predict_maintenance_window(candidate_request)

    print(f"[+] Prediction Generated for {result['request_id']}:")
    print(f"    - Predicted Baseline Delay : {result['predicted_baseline_delay_minutes']:.1f} minutes")
    print(f"    - Affected Trains Overlap  : {result['affected_train_count']} trains")
    print(f"    - Corridor Density         : {result['traffic_density']:.2f}")
    print(f"    - Maintenance Exposure     : {result['maintenance_exposure_score']:.1f} / 100")
    print(f"    - Risk Tier                : {result['risk_category']}")
    print(f"    - Data Quality Status      : {result['data_quality']['status']}")
    print(f"    - Uncertainty Bounds       : {result['uncertainty']['lower_bound_minutes']}m to {result['uncertainty']['upper_bound_minutes']}m")
    print(f"    - Active Warnings          : {result['warnings']}")


def demonstrate_member3_integration():
    print("\n" + "=" * 75)
    print("STEP 3: Member 3 Optimization Engine Candidate Comparison & Pareto Front")
    print("=" * 75)

    mock_optimizer = MockMember3OptimizationEngine()
    results = mock_optimizer.find_best_maintenance_slot("SEC_NDLS_CNB", "2026-10-25")

    ranking = results["ranking_results"]
    pareto = results["pareto_tradeoffs"]

    print(f"[+] Recommended Optimal Slot: {ranking['recommended_request_id']}")
    print(f"    Total Evaluated: {ranking['total_candidates']} (Feasible: {ranking['feasible_candidates']}, Infeasible: {ranking['infeasible_candidates']})\n")

    print(f"{'Rank':<6} {'Request ID':<28} {'Feasible?':<11} {'Score':<9} {'Delay (m)':<11} {'Trains':<8} {'Risk':<10}")
    print("-" * 90)

    for item in ranking["ranked_candidates"]:
        is_feas = item["is_feasible"]
        rec = " [RECOMMENDED]" if item["is_recommended"] else ""
        if is_feas and item["prediction"]:
            p = item["prediction"]
            print(
                f"{item['rank']:<6} {item['candidate_summary']['request_id']:<28} {'YES':<11} "
                f"{p['maintenance_exposure_score']:<9.1f} {p['predicted_baseline_delay_minutes']:<11.1f} "
                f"{p['affected_train_count']:<8} {p['risk_category']:<10}{rec}"
            )
        else:
            err_msg = item['validation_errors'][0][:28] + "..." if item['validation_errors'] else "Unknown"
            print(
                f"{item['rank']:<6} {item['candidate_summary']['request_id']:<28} {'NO':<11} "
                f"{'N/A':<9} {'N/A':<11} {'N/A':<8} {'REJECTED':<10} (Error: {err_msg})"
            )

    print("\n[+] Pareto Trade-Off Analysis (Disruption vs Duration):")
    for p in pareto:
        badge = " [PARETO-OPTIMAL]" if p["is_pareto_optimal"] else ""
        print(f"    - {p['request_id']}: Disruption Score = {p['disruption_score']:.1f}, Duration = {p['duration_minutes']}m{badge}")


def demonstrate_member4_integration():
    print("\n" + "=" * 75)
    print("STEP 4: Member 4 Operational Conflict and Interlocking Certification")
    print("=" * 75)

    mock_validator = MockMember4SafetyValidation()
    req = {
        "request_id": "REQ_SAFETY_CHECK_001",
        "track_section": "SEC_NDLS_CNB",
        "requested_date": "2026-10-25",
        "proposed_start_time": "01:30",
        "proposed_end_time": "04:30",
        "required_duration_minutes": 180.0,
        "maintenance_priority": "HIGH",
    }

    safety_decision = mock_validator.certify_maintenance_block(req)
    print(f"[+] Member 4 Operational Safety Handoff for {req['request_id']}:")
    print(f"    - Certified by Member 4     : {safety_decision['certified_by_member4']}")
    print(f"    - Conflicting Trains Count : {safety_decision['conflicting_trains_count']}")
    print(f"    - Disruption Score Received : {safety_decision['disruption_score_received']:.1f}")
    print(f"    - Risk Tier Received        : {safety_decision['risk_tier_received']}")
    print(f"    - Operational Notes         : {safety_decision['certification_notes']}")
    print(f"    - Boundary Disclaimer       : {safety_decision['disclaimer']}")


def demonstrate_member5_integration():
    print("\n" + "=" * 75)
    print("STEP 5: Member 5 Web UI & Dashboard Platform Metric Display")
    print("=" * 75)

    req = {
        "request_id": "REQ_UI_DISPLAY_001",
        "track_section": "SEC_BCT_ST",
        "requested_date": "2026-10-25",
        "proposed_start_time": "02:00",
        "proposed_end_time": "04:30",
        "required_duration_minutes": 150.0,
        "maintenance_priority": "MEDIUM",
    }
    prediction = predict_maintenance_window(req)
    ui_card = MockMember5WebDashboard.render_summary_card(prediction)

    print(f"[+] UI Display Tokens generated for Member 5:")
    print(f"    - Card Title         : {ui_card['card_title']}")
    print(f"    - Badge Hex Color    : {ui_card['badge_color']}")
    print(f"    - Disruption Index   : {ui_card['disruption_index']}")
    print(f"    - Expected Delay     : {ui_card['predicted_delay']}")
    print(f"    - Affected Services  : {ui_card['affected_services']}")
    print(f"    - Data Quality Badge : {ui_card['quality_status']}")


def demonstrate_error_and_ood_handling():
    print("\n" + "=" * 75)
    print("STEP 6: Robust Error & Out-Of-Distribution (OOD) Handling")
    print("=" * 75)

    # 1. Out-of-Distribution Input (Delay > 180 min)
    ood_req = {
        "request_id": "REQ_OOD_DEMO",
        "track_section": "SEC_NDLS_CNB",
        "requested_date": "2026-10-25",
        "proposed_start_time": "01:30",
        "proposed_end_time": "04:30",
        "required_duration_minutes": 180.0,
        "maintenance_priority": "HIGH",
        "existing_delay_minutes": 210.0,  # OOD!
    }
    pred_ood = predict_maintenance_window(ood_req)
    print(f"[OK] Handled Out-of-Distribution existing delay:")
    print(f"     Status: {pred_ood['data_quality']['status']}")
    print(f"     Warnings: {pred_ood['data_quality']['warnings']}")

    # 2. Fatal Infeasible Request (30 hours duration)
    bad_req = {
        "request_id": "REQ_FATAL_ERR",
        "track_section": "SEC_NDLS_CNB",
        "requested_date": "2026-10-25",
        "proposed_start_time": "01:30",
        "proposed_end_time": "04:30",
        "required_duration_minutes": 1800.0,  # Impossible!
    }
    try:
        predict_maintenance_window(bad_req)
    except ValueError as e:
        print(f"[OK] Caught expected fatal input error:\n     '{e}'")


if __name__ == "__main__":
    print("\n" + "=" * 75)
    print(">>> KAVACH BIE MEMBER 2: FULL TEAM INTEGRATION WALKTHROUGH <<<")
    print("=" * 75)
    demonstrate_member1_integration()
    demonstrate_single_window_prediction()
    demonstrate_member3_integration()
    demonstrate_member4_integration()
    demonstrate_member5_integration()
    demonstrate_error_and_ood_handling()
    print("\n" + "=" * 75)
    print(">>> ALL 6 CROSS-MODULE DEMONSTRATIONS COMPLETED SUCCESSFULLY <<<")
    print("=" * 75 + "\n")
