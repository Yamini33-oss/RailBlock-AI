"""
===============================================================================
KAVACH BIE — Member 2: AI/ML Train Delay Prediction Module
Data Loader and Team Data Adapter Layer
===============================================================================
Provides reliable data loading, validation pipeline execution, and schema
adaptation routines. If synthetic data files are not yet present on disk,
it provides auto-generation fallback for zero-friction initial setup.

Includes an explicit Data Adapter Layer to map Member 1's real or staging
datasets into the canonical schema expected by Member 2's prediction pipeline.
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

from config import (
    DELAYS_DATA_FILE,
    MAINTENANCE_DATA_FILE,
    SCHEDULES_DATA_FILE,
    TRAFFIC_DATA_FILE,
)
from data_validator import DataValidator, ValidationResult
from generate_data import generate_synthetic_data, save_synthetic_datasets

logger = logging.getLogger("kavach_bie.data_loader")


# Canonical column alias mappings for Member 1 schema harmonization
DEFAULT_COLUMN_ALIASES: Dict[str, Dict[str, str]] = {
    "delays": {
        "train_no": "train_number",
        "trn_no": "train_number",
        "train_id": "train_number",
        "section": "track_section",
        "section_id": "track_section",
        "section_code": "track_section",
        "date": "service_date",
        "run_date": "service_date",
        "sch_arr": "scheduled_arrival",
        "act_arr": "actual_arrival",
        "sch_dep": "scheduled_departure",
        "act_dep": "actual_departure",
        "delay": "historical_delay_minutes",
        "delay_mins": "historical_delay_minutes",
        "arr_delay": "historical_delay_minutes",
    },
    "schedules": {
        "train_no": "train_number",
        "src": "source",
        "dest": "destination",
        "dst": "destination",
        "section": "track_section",
        "sch_arr": "scheduled_arrival",
        "sch_dep": "scheduled_departure",
        "running_time": "scheduled_running_time_minutes",
    },
    "traffic": {
        "section": "track_section",
        "date": "observation_date",
        "period": "time_period",
        "density": "traffic_density",
        "train_count": "scheduled_train_count",
        "utilization": "track_utilization",
    },
    "maintenance": {
        "id": "request_id",
        "req_id": "request_id",
        "section": "track_section",
        "date": "requested_date",
        "start_time": "proposed_start_time",
        "end_time": "proposed_end_time",
        "duration": "required_duration_minutes",
        "duration_minutes": "required_duration_minutes",
        "priority": "maintenance_priority",
    },
}


class DataLoader:
    """Loads, validates, and adapts railway datasets for the ML pipeline."""

    def __init__(self, data_dir: Optional[Path] = None, auto_generate: bool = True):
        self.auto_generate = auto_generate
        self.validator = DataValidator()

    def _ensure_data_exists(self) -> None:
        """Check if default data files exist; generate if missing and auto_generate is enabled."""
        if not DELAYS_DATA_FILE.exists() or not SCHEDULES_DATA_FILE.exists():
            if self.auto_generate:
                logger.info("Default sample datasets not found. Generating synthetic datasets...")
                datasets = generate_synthetic_data()
                save_synthetic_datasets(datasets)
                logger.info("Synthetic datasets created successfully.")
            else:
                raise FileNotFoundError(
                    f"Required dataset files missing in {DELAYS_DATA_FILE.parent} and auto_generate=False."
                )

    def load_delays(self, file_path: Optional[Path] = None, validate: bool = True) -> pd.DataFrame:
        """Load and validate historical train delays."""
        target_path = Path(file_path) if file_path else DELAYS_DATA_FILE
        if not target_path.exists():
            self._ensure_data_exists()

        df = pd.read_csv(target_path, dtype={"train_number": str})
        if validate:
            res: ValidationResult = self.validator.validate_delays_dataframe(df)
            if not res.is_valid:
                raise ValueError(f"Historical delays validation failed: {res.errors}")
            return res.cleaned_df
        return df

    def load_schedules(self, file_path: Optional[Path] = None, validate: bool = True) -> pd.DataFrame:
        """Load and validate timetabled train schedules."""
        target_path = Path(file_path) if file_path else SCHEDULES_DATA_FILE
        if not target_path.exists():
            self._ensure_data_exists()

        df = pd.read_csv(target_path, dtype={"train_number": str})
        if validate:
            res: ValidationResult = self.validator.validate_schedules_dataframe(df)
            if not res.is_valid:
                raise ValueError(f"Schedules validation failed: {res.errors}")
            return res.cleaned_df
        return df

    def load_traffic(self, file_path: Optional[Path] = None, validate: bool = True) -> pd.DataFrame:
        """Load and validate corridor traffic density records."""
        target_path = Path(file_path) if file_path else TRAFFIC_DATA_FILE
        if not target_path.exists():
            self._ensure_data_exists()

        df = pd.read_csv(target_path)
        if validate:
            res: ValidationResult = self.validator.validate_traffic_dataframe(df)
            if not res.is_valid:
                raise ValueError(f"Traffic density validation failed: {res.errors}")
            return res.cleaned_df
        return df

    def load_maintenance(self, file_path: Optional[Path] = None) -> pd.DataFrame:
        """Load proposed maintenance window requests."""
        target_path = Path(file_path) if file_path else MAINTENANCE_DATA_FILE
        if not target_path.exists():
            self._ensure_data_exists()

        return pd.read_csv(target_path)

    def load_all(self, validate: bool = True) -> Dict[str, pd.DataFrame]:
        """Load all four railway datasets and persist data quality audit report."""
        self._ensure_data_exists()
        datasets = {
            "delays": self.load_delays(validate=validate),
            "schedules": self.load_schedules(validate=validate),
            "traffic": self.load_traffic(validate=validate),
            "maintenance": self.load_maintenance(),
        }
        # Persist data quality audit summary
        DataValidator.generate_and_save_data_quality_report(datasets)
        return datasets


    @staticmethod
    def adapt_schema(
        df: pd.DataFrame,
        dataset_type: str,
        custom_mapping: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        """
        Adapter layer to convert external (Member 1) datasets to Member 2's schema.
        Maps column aliases and drops extraneous columns if necessary.
        """
        if df is None or not isinstance(df, pd.DataFrame):
            raise ValueError("Input to adapt_schema must be a valid pandas DataFrame.")

        adapted_df = df.copy()

        # Apply default known aliases
        default_mapping = DEFAULT_COLUMN_ALIASES.get(dataset_type, {})
        full_mapping = {**default_mapping, **(custom_mapping or {})}

        rename_dict = {}
        for col in adapted_df.columns:
            normalized_col = str(col).strip().lower()
            if normalized_col in full_mapping:
                rename_dict[col] = full_mapping[normalized_col]

        if rename_dict:
            adapted_df = adapted_df.rename(columns=rename_dict)
            logger.info("Adapted columns for %s: %s", dataset_type, rename_dict)

        return adapted_df
