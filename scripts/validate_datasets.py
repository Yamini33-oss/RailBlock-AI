"""Dataset validation and quality reporting for KAVACH BIE Member 3.

Performs automated data quality assertions across all processed datasets:
- Schema completeness & expected columns
- Missing value thresholds
- Duplicate record detection
- Foreign key & referential integrity (trains <-> schedules <-> stations)
- Date and time format validity
Outputs: data/reports/data_quality_report.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "data" / "reports"
QUALITY_REPORT_FILE = REPORTS_DIR / "data_quality_report.json"


def validate_stations(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate stations dataset."""
    req_cols = ["station_code", "station_name", "state", "zone"]
    missing_cols = [c for c in req_cols if c not in df.columns]

    null_codes = int(df["station_code"].isna().sum()) if "station_code" in df.columns else len(df)
    empty_codes = int((df["station_code"].str.strip() == "").sum()) if "station_code" in df.columns else len(df)
    duplicates = int(df.duplicated(subset=["station_code"]).sum()) if "station_code" in df.columns else 0

    passed = (len(missing_cols) == 0 and null_codes == 0 and empty_codes == 0 and duplicates == 0 and len(df) > 5000)

    return {
        "dataset": "stations_processed.csv",
        "passed": passed,
        "row_count": len(df),
        "column_count": len(df.columns),
        "missing_columns": missing_cols,
        "null_station_codes": null_codes,
        "empty_station_codes": empty_codes,
        "duplicate_codes": duplicates,
        "unique_zones": int(df["zone"].nunique()) if "zone" in df.columns else 0,
        "unique_states": int(df["state"].nunique()) if "state" in df.columns else 0,
    }


def validate_trains(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate trains dataset."""
    req_cols = ["train_number", "train_name", "train_type", "from_station_code", "to_station_code", "departure_time", "arrival_time"]
    missing_cols = [c for c in req_cols if c not in df.columns]

    null_nums = int(df["train_number"].isna().sum()) if "train_number" in df.columns else len(df)
    duplicates = int(df.duplicated(subset=["train_number"]).sum()) if "train_number" in df.columns else 0

    # Validate time formats HH:MM:SS
    time_format_errors = 0
    if "departure_time" in df.columns:
        invalid_dep = pd.to_datetime(df["departure_time"], format="%H:%M:%S", errors="coerce").isna().sum()
        time_format_errors += int(invalid_dep)

    passed = (len(missing_cols) == 0 and null_nums == 0 and duplicates == 0 and len(df) > 1000)

    return {
        "dataset": "trains_processed.csv",
        "passed": passed,
        "row_count": len(df),
        "column_count": len(df.columns),
        "missing_columns": missing_cols,
        "null_train_numbers": null_nums,
        "duplicate_train_numbers": duplicates,
        "time_format_errors": time_format_errors,
        "unique_train_types": list(df["train_type"].unique()[:8]) if "train_type" in df.columns else [],
    }


def validate_schedules(df: pd.DataFrame, station_codes: set, train_numbers: set) -> Dict[str, Any]:
    """Validate schedules dataset and cross-reference with stations and trains."""
    req_cols = ["stop_id", "train_number", "station_code", "day", "arrival_time", "departure_time"]
    missing_cols = [c for c in req_cols if c not in df.columns]

    null_stops = int(df["stop_id"].isna().sum()) if "stop_id" in df.columns else len(df)
    duplicates = int(df.duplicated(subset=["stop_id"]).sum()) if "stop_id" in df.columns else 0

    # Referential checks
    sched_stations = set(df["station_code"].str.upper().dropna().unique())
    sched_trains = set(df["train_number"].astype(str).str.zfill(5).dropna().unique())

    unknown_stations = len(sched_stations - station_codes)
    unknown_trains = len(sched_trains - train_numbers)

    passed = (len(missing_cols) == 0 and null_stops == 0 and duplicates == 0 and len(df) > 100000)

    return {
        "dataset": "schedules_processed.csv",
        "passed": passed,
        "row_count": len(df),
        "column_count": len(df.columns),
        "missing_columns": missing_cols,
        "null_stop_ids": null_stops,
        "duplicate_stops": duplicates,
        "total_referenced_trains": len(sched_trains),
        "total_referenced_stations": len(sched_stations),
        "unknown_stations_count": unknown_stations,
        "unknown_trains_count": unknown_trains,
    }


def validate_traffic_density(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate derived section traffic density."""
    req_cols = ["track_section_id", "hour_of_day", "scheduled_train_count", "traffic_density_score", "density_category"]
    missing_cols = [c for c in req_cols if c not in df.columns]

    score_in_range = ((df["traffic_density_score"] >= 0.0) & (df["traffic_density_score"] <= 1.0)).all()
    categories_valid = df["density_category"].isin(["LOW", "MEDIUM", "HIGH"]).all()

    passed = (len(missing_cols) == 0 and score_in_range and categories_valid and len(df) > 0)

    return {
        "dataset": "section_traffic_density_processed.csv",
        "passed": passed,
        "row_count": len(df),
        "column_count": len(df.columns),
        "missing_columns": missing_cols,
        "score_range_valid": bool(score_in_range),
        "categories_valid": bool(categories_valid),
        "monitored_sections_count": int(df["track_section_id"].nunique()),
    }


def validate_all_datasets() -> Dict[str, Any]:
    """Execute validation suite across all processed files."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Executing dataset validation suite...")

    stations_df = pd.read_csv(PROCESSED_DIR / "stations_processed.csv")
    trains_df = pd.read_csv(PROCESSED_DIR / "trains_processed.csv")
    schedules_df = pd.read_csv(PROCESSED_DIR / "schedules_processed.csv")
    density_df = pd.read_csv(PROCESSED_DIR / "section_traffic_density_processed.csv")

    station_codes = set(stations_df["station_code"].str.upper().dropna().unique())
    train_numbers = set(trains_df["train_number"].astype(str).str.zfill(5).dropna().unique())

    report = {
        "validation_version": "1.0.0",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "PASSED",
        "datasets": {
            "stations": validate_stations(stations_df),
            "trains": validate_trains(trains_df),
            "schedules": validate_schedules(schedules_df, station_codes, train_numbers),
            "traffic_density": validate_traffic_density(density_df),
        },
    }

    all_passed = all(d["passed"] for d in report["datasets"].values())
    report["overall_status"] = "PASSED" if all_passed else "FAILED"

    with open(QUALITY_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(
        "Validation completed. Overall status: %s. Report saved to %s",
        report["overall_status"],
        QUALITY_REPORT_FILE,
    )
    return report


if __name__ == "__main__":
    validate_all_datasets()
