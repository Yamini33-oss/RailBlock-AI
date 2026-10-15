"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Data Validation and Quality Assurance
===============================================================================
Provides robust, reusable data validation routines for all railway datasets:
- Historical train delays
- Timetabled train schedules
- Corridor traffic density
- Maintenance window requests

Distinguishes between fatal errors (which reject records) and non-fatal warnings
(which trigger graceful fallbacks or imputations).
"""

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

import json
from pathlib import Path
from config import (
    DATA_QUALITY_REPORT_JSON,
    KNOWN_TRACK_SECTIONS,
    MAX_WINDOW_DURATION_HOURS,
    OOD_MAX_DURATION_MINUTES,
    OOD_MAX_EXISTING_DELAY,
    OOD_MAX_TRAFFIC_DENSITY,
)



@dataclass
class ValidationResult:
    """Encapsulates the outcome of validating a dataset."""

    is_valid: bool
    cleaned_df: pd.DataFrame
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rows_rejected: int = 0
    rows_original: int = 0


# Required column definitions for each table
REQUIRED_DELAYS_COLUMNS: Set[str] = {
    "train_number",
    "train_name",
    "service_date",
    "track_section",
    "scheduled_arrival",
    "actual_arrival",
    "scheduled_departure",
    "actual_departure",
    "historical_delay_minutes",
}

REQUIRED_SCHEDULES_COLUMNS: Set[str] = {
    "train_number",
    "train_name",
    "source",
    "destination",
    "track_section",
    "scheduled_arrival",
    "scheduled_departure",
    "scheduled_running_time_minutes",
}

REQUIRED_TRAFFIC_COLUMNS: Set[str] = {
    "track_section",
    "observation_date",
    "time_period",
    "traffic_density",
    "scheduled_train_count",
    "track_utilization",
}

REQUIRED_MAINTENANCE_COLUMNS: Set[str] = {
    "request_id",
    "track_section",
    "requested_date",
    "proposed_start_time",
    "proposed_end_time",
    "required_duration_minutes",
}


def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Parse HH:MM or HH:MM:SS string into minutes from midnight (0 to 1439)."""
    if pd.isna(time_str):
        return None
    s = str(time_str).strip()
    match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return hours * 60 + minutes


def calculate_window_span_minutes(start_str: str, end_str: str) -> Optional[int]:
    """Calculate the clock span in minutes between start and end times, handling midnight rollover."""
    start_m = parse_time_to_minutes(start_str)
    end_m = parse_time_to_minutes(end_str)
    if start_m is None or end_m is None:
        return None
    if end_m >= start_m:
        return end_m - start_m
    else:
        # Rollover past midnight (e.g. 23:00 to 03:00)
        return (1440 - start_m) + end_m


class DataValidator:
    """Validates and cleans railway data frames and real-time inference payloads."""

    @staticmethod
    def validate_delays_dataframe(df: pd.DataFrame) -> ValidationResult:
        """Validate historical train delay records."""
        errors: List[str] = []
        warnings: List[str] = []

        if df is None or not isinstance(df, pd.DataFrame):
            return ValidationResult(
                is_valid=False,
                cleaned_df=pd.DataFrame(),
                errors=["Input is not a valid pandas DataFrame."],
                rows_rejected=0,
                rows_original=0,
            )

        rows_original = len(df)
        if rows_original == 0:
            return ValidationResult(
                is_valid=False,
                cleaned_df=df.copy(),
                errors=["Historical delays dataset is completely empty."],
                rows_rejected=0,
                rows_original=0,
            )

        # Check required columns
        missing_cols = REQUIRED_DELAYS_COLUMNS - set(df.columns)
        if missing_cols:
            errors.append(f"Missing required columns in delays data: {sorted(list(missing_cols))}")
            return ValidationResult(
                is_valid=False,
                cleaned_df=df.copy(),
                errors=errors,
                rows_rejected=rows_original,
                rows_original=rows_original,
            )

        clean_df = df.copy()

        # Handle duplicates
        init_len = len(clean_df)
        clean_df = clean_df.drop_duplicates()
        if len(clean_df) < init_len:
            warnings.append(f"Dropped {init_len - len(clean_df)} duplicate rows from delays data.")

        # Validate date format
        invalid_dates = []
        for idx, val in clean_df["service_date"].items():
            try:
                datetime.strptime(str(val).strip(), "%Y-%m-%d")
            except Exception:
                invalid_dates.append(idx)

        if invalid_dates:
            errors.append(f"Found {len(invalid_dates)} rows with invalid service_date format (expected YYYY-MM-DD).")
            clean_df = clean_df.drop(index=invalid_dates)

        # Validate delay numeric and non-negative
        clean_df["historical_delay_minutes"] = pd.to_numeric(clean_df["historical_delay_minutes"], errors="coerce")
        nan_delays = clean_df[clean_df["historical_delay_minutes"].isna()].index
        if len(nan_delays) > 0:
            errors.append(f"Dropped {len(nan_delays)} rows with non-numeric historical_delay_minutes.")
            clean_df = clean_df.drop(index=nan_delays)

        negative_delays = clean_df[clean_df["historical_delay_minutes"] < 0].index
        if len(negative_delays) > 0:
            warnings.append(
                f"Detected {len(negative_delays)} rows with negative delay. Clipped negative delays to 0.0 minutes."
            )
            clean_df.loc[negative_delays, "historical_delay_minutes"] = 0.0

        # Validate track sections
        unknown_sections = set(clean_df["track_section"].dropna()) - set(KNOWN_TRACK_SECTIONS.keys())
        if unknown_sections:
            warnings.append(f"Delays data contains unfamiliar track sections: {sorted(list(unknown_sections))}.")

        rows_rejected = rows_original - len(clean_df)
        is_valid = len(clean_df) > 0 and len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            cleaned_df=clean_df,
            errors=errors,
            warnings=warnings,
            rows_rejected=rows_rejected,
            rows_original=rows_original,
        )

    @staticmethod
    def validate_schedules_dataframe(df: pd.DataFrame) -> ValidationResult:
        """Validate train timetables and schedule records."""
        errors: List[str] = []
        warnings: List[str] = []

        if df is None or not isinstance(df, pd.DataFrame):
            return ValidationResult(
                is_valid=False,
                cleaned_df=pd.DataFrame(),
                errors=["Input is not a valid pandas DataFrame."],
            )

        rows_original = len(df)
        if rows_original == 0:
            return ValidationResult(
                is_valid=False,
                cleaned_df=df.copy(),
                errors=["Schedules dataset is completely empty."],
            )

        missing_cols = REQUIRED_SCHEDULES_COLUMNS - set(df.columns)
        if missing_cols:
            return ValidationResult(
                is_valid=False,
                cleaned_df=df.copy(),
                errors=[f"Missing required columns in schedules: {sorted(list(missing_cols))}"],
                rows_rejected=rows_original,
                rows_original=rows_original,
            )

        clean_df = df.copy().drop_duplicates()
        if len(clean_df) < rows_original:
            warnings.append(f"Dropped {rows_original - len(clean_df)} duplicate schedule records.")

        # Ensure valid time formats for scheduled arrival and departure
        invalid_time_rows = []
        for idx, row in clean_df.iterrows():
            arr_m = parse_time_to_minutes(row["scheduled_arrival"])
            dep_m = parse_time_to_minutes(row["scheduled_departure"])
            if arr_m is None or dep_m is None:
                invalid_time_rows.append(idx)

        if invalid_time_rows:
            warnings.append(f"Dropped {len(invalid_time_rows)} schedule rows with unparseable arrival/departure times.")
            clean_df = clean_df.drop(index=invalid_time_rows)

        # Validate scheduled running time is positive
        clean_df["scheduled_running_time_minutes"] = pd.to_numeric(
            clean_df["scheduled_running_time_minutes"], errors="coerce"
        )
        non_positive = clean_df[clean_df["scheduled_running_time_minutes"] <= 0].index
        if len(non_positive) > 0:
            warnings.append(f"Found {len(non_positive)} schedules with non-positive running time. Dropping them.")
            clean_df = clean_df.drop(index=non_positive)

        rows_rejected = rows_original - len(clean_df)
        is_valid = len(clean_df) > 0 and len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            cleaned_df=clean_df,
            errors=errors,
            warnings=warnings,
            rows_rejected=rows_rejected,
            rows_original=rows_original,
        )

    @staticmethod
    def validate_traffic_dataframe(df: pd.DataFrame) -> ValidationResult:
        """Validate track section traffic density logs."""
        errors: List[str] = []
        warnings: List[str] = []

        if df is None or not isinstance(df, pd.DataFrame):
            return ValidationResult(
                is_valid=False,
                cleaned_df=pd.DataFrame(),
                errors=["Input is not a valid pandas DataFrame."],
            )

        rows_original = len(df)
        if rows_original == 0:
            return ValidationResult(
                is_valid=False,
                cleaned_df=df.copy(),
                errors=["Traffic density dataset is completely empty."],
            )

        missing_cols = REQUIRED_TRAFFIC_COLUMNS - set(df.columns)
        if missing_cols:
            return ValidationResult(
                is_valid=False,
                cleaned_df=df.copy(),
                errors=[f"Missing required columns in traffic density: {sorted(list(missing_cols))}"],
                rows_rejected=rows_original,
                rows_original=rows_original,
            )

        clean_df = df.copy().drop_duplicates()

        # Numeric conversions
        for col in ["traffic_density", "scheduled_train_count", "track_utilization"]:
            clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")

        invalid_num_rows = clean_df[
            clean_df["traffic_density"].isna()
            | clean_df["scheduled_train_count"].isna()
            | clean_df["track_utilization"].isna()
        ].index
        if len(invalid_num_rows) > 0:
            warnings.append(f"Dropped {len(invalid_num_rows)} traffic rows with non-numeric metrics.")
            clean_df = clean_df.drop(index=invalid_num_rows)

        # Range checks: density and utilization should be non-negative
        out_of_range = clean_df[
            (clean_df["traffic_density"] < 0)
            | (clean_df["traffic_density"] > 2.5)
            | (clean_df["scheduled_train_count"] < 0)
            | (clean_df["track_utilization"] < 0)
        ].index
        if len(out_of_range) > 0:
            warnings.append(f"Found {len(out_of_range)} traffic rows with out-of-range metrics; dropping them.")
            clean_df = clean_df.drop(index=out_of_range)

        rows_rejected = rows_original - len(clean_df)
        is_valid = len(clean_df) > 0 and len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            cleaned_df=clean_df,
            errors=errors,
            warnings=warnings,
            rows_rejected=rows_rejected,
            rows_original=rows_original,
        )

    @staticmethod
    def validate_single_request(request: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate and sanitize a single maintenance window request dictionary.
        Returns (sanitized_request_dict, list_of_warnings).
        Raises ValueError with clear diagnostics if fatal invalidity is detected.
        """
        warnings: List[str] = []

        if not isinstance(request, dict):
            raise ValueError(f"Request payload must be a dictionary, got {type(request).__name__}.")

        # Check required fields
        for field_name in REQUIRED_MAINTENANCE_COLUMNS:
            if field_name not in request or request[field_name] is None:
                raise ValueError(f"Missing required maintenance request field: '{field_name}'.")

        req_id = str(request["request_id"]).strip()
        if not req_id:
            raise ValueError("Field 'request_id' cannot be blank.")

        section = str(request["track_section"]).strip()
        if not section:
            raise ValueError("Field 'track_section' cannot be blank.")
        if section not in KNOWN_TRACK_SECTIONS:
            warnings.append(
                f"Track section '{section}' is not in the known corridor registry. Proceeding with caution."
            )

        # Date validation
        date_str = str(request["requested_date"]).strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            raise ValueError(f"Invalid date '{date_str}'. Expected format YYYY-MM-DD.")

        # Time validation
        start_str = str(request["proposed_start_time"]).strip()
        end_str = str(request["proposed_end_time"]).strip()
        start_m = parse_time_to_minutes(start_str)
        end_m = parse_time_to_minutes(end_str)

        if start_m is None:
            raise ValueError(f"Invalid proposed_start_time '{start_str}'. Expected 24-hr format HH:MM.")
        if end_m is None:
            raise ValueError(f"Invalid proposed_end_time '{end_str}'. Expected 24-hr format HH:MM.")

        # Duration validation
        try:
            duration = float(request["required_duration_minutes"])
        except (ValueError, TypeError):
            raise ValueError(
                f"Field 'required_duration_minutes' must be a valid number, got '{request.get('required_duration_minutes')}'."
            )

        if duration <= 0:
            raise ValueError(f"Required duration must be strictly positive (> 0), got {duration} mins.")
        if duration > MAX_WINDOW_DURATION_HOURS * 60:
            raise ValueError(
                f"Requested duration ({duration} mins) exceeds maximum allowed track possession of {MAX_WINDOW_DURATION_HOURS * 60} mins (24 hours)."
            )

        # Check window span consistency
        span_m = calculate_window_span_minutes(start_str, end_str)
        if span_m is not None and abs(span_m - duration) > 1.0:
            warnings.append(
                f"Discrepancy detected: Clock span from {start_str} to {end_str} is {span_m} minutes, "
                f"while required_duration_minutes is specified as {duration} minutes. Using {duration} mins."
            )

        # Priority validation and normalization
        raw_priority = request.get("maintenance_priority")
        if raw_priority is None or pd.isna(raw_priority):
            priority = "MEDIUM"
            warnings.append("Missing 'maintenance_priority'; defaulted to 'MEDIUM'.")
        else:
            priority = str(raw_priority).strip().upper()
            if priority not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
                warnings.append(f"Unrecognized priority '{raw_priority}'; defaulted to 'MEDIUM'.")
                priority = "MEDIUM"

        # Optional traffic density
        traffic_density = request.get("traffic_density")
        if traffic_density is not None:
            try:
                traffic_density = float(traffic_density)
                if traffic_density < 0.0 or traffic_density > 2.0:
                    warnings.append(
                        f"Unusual traffic_density value ({traffic_density}); clipping to valid [0.0, 2.0] range."
                    )
                    traffic_density = max(0.0, min(traffic_density, 2.0))
            except (ValueError, TypeError):
                warnings.append(f"Non-numeric traffic_density '{traffic_density}'; resetting to None (auto-lookup).")
                traffic_density = None

        # Optional existing delay
        existing_delay = request.get("existing_delay_minutes")
        if existing_delay is not None:
            try:
                existing_delay = max(0.0, float(existing_delay))
            except (ValueError, TypeError):
                warnings.append(f"Non-numeric existing_delay_minutes '{existing_delay}'; resetting to 0.0.")
                existing_delay = 0.0

        is_ood = False
        imputations: List[str] = []

        if raw_priority is None or pd.isna(raw_priority):
            imputations.append("maintenance_priority defaulted to 'MEDIUM'")
        if traffic_density is None:
            imputations.append("traffic_density omitted by caller; will use corridor-period historical median")

        # Out-of-distribution (OOD) checks
        if traffic_density is not None and traffic_density > OOD_MAX_TRAFFIC_DENSITY:
            warnings.append(
                f"OOD Warning: Traffic density ({traffic_density:.2f}) exceeds typical saturation threshold ({OOD_MAX_TRAFFIC_DENSITY})."
            )
            is_ood = True

        if existing_delay is not None and existing_delay > OOD_MAX_EXISTING_DELAY:
            warnings.append(
                f"OOD Warning: Existing delay ({existing_delay:.1f} mins) exceeds extreme corridor delay threshold ({OOD_MAX_EXISTING_DELAY} mins)."
            )
            is_ood = True

        if duration > OOD_MAX_DURATION_MINUTES:
            warnings.append(
                f"OOD Warning: Required duration ({duration:.0f} mins) exceeds standard 12-hr maintenance slot."
            )
            is_ood = True

        sanitized: Dict[str, Any] = {
            "request_id": req_id,
            "track_section": section,
            "requested_date": date_str,
            "proposed_start_time": start_str,
            "proposed_end_time": end_str,
            "required_duration_minutes": duration,
            "maintenance_priority": priority,
            "traffic_density": traffic_density,
            "existing_delay_minutes": existing_delay,
        }

        return sanitized, warnings

    @staticmethod
    def validate_single_request_detailed(
        request: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str], List[str], bool]:
        """
        Extended single request validation returning:
        (sanitized_dict, warnings, imputations, is_out_of_distribution)
        """
        # Run standard validation
        sanitized, warnings = DataValidator.validate_single_request(request)

        # Track imputations
        imputations: List[str] = []
        if request.get("maintenance_priority") is None:
            imputations.append("maintenance_priority: defaulted to 'MEDIUM'")
        if request.get("traffic_density") is None:
            imputations.append("traffic_density: omitted; using corridor schedule median")
        if request.get("existing_delay_minutes") is None:
            imputations.append("existing_delay_minutes: omitted; defaulted to 0.0")

        # Check OOD
        is_ood = False
        td = sanitized.get("traffic_density")
        if td is not None and td > OOD_MAX_TRAFFIC_DENSITY:
            is_ood = True
        ed = sanitized.get("existing_delay_minutes")
        if ed is not None and ed > OOD_MAX_EXISTING_DELAY:
            is_ood = True
        dur = sanitized.get("required_duration_minutes", 0)
        if dur > OOD_MAX_DURATION_MINUTES:
            is_ood = True

        return sanitized, warnings, imputations, is_ood

    @staticmethod
    def audit_dataset_quality(df: pd.DataFrame, dataset_name: str) -> Dict[str, Any]:
        """Audit record counts, duplicates, missing values, and columns for a DataFrame."""
        if df is None or not isinstance(df, pd.DataFrame):
            return {
                "dataset_name": dataset_name,
                "status": "INVALID",
                "error": "Dataset is not a pandas DataFrame",
                "total_rows": 0,
            }

        total_rows = len(df)
        total_cols = len(df.columns)
        dup_count = int(df.duplicated().sum())
        null_counts = df.isnull().sum().to_dict()

        return {
            "dataset_name": dataset_name,
            "status": "VALID" if total_rows > 0 and dup_count == 0 else "WARNING",
            "total_rows": total_rows,
            "total_columns": total_cols,
            "duplicate_rows": dup_count,
            "missing_values_per_column": {k: int(v) for k, v in null_counts.items() if v > 0},
            "columns": list(df.columns),
        }

    @staticmethod
    def generate_and_save_data_quality_report(
        datasets_dict: Dict[str, pd.DataFrame],
        output_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate and persist a complete data quality audit report."""
        target_path = output_file or DATA_QUALITY_REPORT_JSON
        audit_results = {}

        for name, df in datasets_dict.items():
            audit_results[name] = DataValidator.audit_dataset_quality(df, dataset_name=name)

        overall_status = "HEALTHY"
        for name, res in audit_results.items():
            if res.get("duplicate_rows", 0) > 0 or len(res.get("missing_values_per_column", {})) > 0:
                overall_status = "WARNING"
            if res.get("total_rows", 0) == 0:
                overall_status = "CRITICAL"

        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "audits": audit_results,
        }

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

