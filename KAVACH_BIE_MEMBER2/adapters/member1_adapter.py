"""
===============================================================================
KAVACH BIE — Member 2: Integration Adapter for Member 1
Member 1: Data Management, Ingestion & Infrastructure Database
===============================================================================
Provides a resilient adapter layer for Member 1's upstream data pipelines:
- Ingests raw DataFrames or CSV files from Member 1's ingestion subsystem.
- Harmonizes external/inconsistent column names to Member 2's canonical schema.
- Executes data quality profiling and generates structured audit summaries.
- Validates data formats (ISO dates, 24-hr times, non-negative delays).
- Persists harmonized files into Member 2's data directory if requested.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import pandas as pd

from config import DATA_DIR
from data_loader import DataLoader
from data_validator import DataValidator, ValidationResult

logger = logging.getLogger("kavach_bie.adapter.member1")


class Member1DataAdapter:
    """Adapter for Member 1 (Data Ingestion & DB)."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.validator = DataValidator()

    def harmonize_and_validate_delays(
        self,
        raw_df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, str]] = None,
        save_to_data_dir: bool = False,
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """
        Harmonize Member 1 delay records, validate them, and optionally persist.
        """
        # Step 1: Adapt column naming aliases
        adapted_df = DataLoader.adapt_schema(
            raw_df,
            dataset_type="delays",
            custom_mapping=custom_mapping,
        )

        # Step 2: Validate through DataValidator
        validation_res = self.validator.validate_delays_dataframe(adapted_df)

        # Step 3: Persist if clean and requested
        if save_to_data_dir and validation_res.is_valid:
            target_path = self.data_dir / "sample_train_delays.csv"
            validation_res.cleaned_df.to_csv(target_path, index=False)
            logger.info("Saved harmonized delays data to %s", target_path)

        return validation_res.cleaned_df, validation_res

    def harmonize_and_validate_schedules(
        self,
        raw_df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, str]] = None,
        save_to_data_dir: bool = False,
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Harmonize and validate Member 1 timetabled schedules."""
        adapted_df = DataLoader.adapt_schema(
            raw_df,
            dataset_type="schedules",
            custom_mapping=custom_mapping,
        )
        validation_res = self.validator.validate_schedules_dataframe(adapted_df)

        if save_to_data_dir and validation_res.is_valid:
            target_path = self.data_dir / "sample_train_schedules.csv"
            validation_res.cleaned_df.to_csv(target_path, index=False)
            logger.info("Saved harmonized schedules data to %s", target_path)

        return validation_res.cleaned_df, validation_res

    def harmonize_and_validate_traffic(
        self,
        raw_df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, str]] = None,
        save_to_data_dir: bool = False,
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Harmonize and validate Member 1 traffic density logs."""
        adapted_df = DataLoader.adapt_schema(
            raw_df,
            dataset_type="traffic",
            custom_mapping=custom_mapping,
        )
        validation_res = self.validator.validate_traffic_dataframe(adapted_df)

        if save_to_data_dir and validation_res.is_valid:
            target_path = self.data_dir / "sample_traffic_density.csv"
            validation_res.cleaned_df.to_csv(target_path, index=False)
            logger.info("Saved harmonized traffic data to %s", target_path)

        return validation_res.cleaned_df, validation_res

    def audit_incoming_batch(
        self,
        delays_df: Optional[pd.DataFrame] = None,
        schedules_df: Optional[pd.DataFrame] = None,
        traffic_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Generate a data quality report for incoming Member 1 data tables."""
        audit_dict = {}
        if delays_df is not None:
            audit_dict["delays"] = self.validator.audit_dataset_quality(delays_df, "incoming_delays")
        if schedules_df is not None:
            audit_dict["schedules"] = self.validator.audit_dataset_quality(schedules_df, "incoming_schedules")
        if traffic_df is not None:
            audit_dict["traffic"] = self.validator.audit_dataset_quality(traffic_df, "incoming_traffic")

        return audit_dict
