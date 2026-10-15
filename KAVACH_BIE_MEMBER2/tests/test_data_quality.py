"""
===============================================================================
Unit Tests: Data Quality Auditing and OOD Detection (data_validator.py)
===============================================================================
Tests dataset quality audits, missing value reports, duplicate detection,
and Out-Of-Distribution (OOD) operational input indicators.
"""

from pathlib import Path
import pandas as pd
import pytest

from data_validator import DataValidator
from predict_delay import predict_maintenance_window


class TestDataQualityAudit:
    """Tests for data quality reporting and OOD checks."""

    def test_audit_dataset_quality_metrics(self):
        sample_df = pd.DataFrame(
            [
                {"id": 1, "val": 10.0},
                {"id": 2, "val": None},
                {"id": 1, "val": 10.0},  # Duplicate
            ]
        )

        audit = DataValidator.audit_dataset_quality(sample_df, dataset_name="test_data")
        assert audit["total_rows"] == 3
        assert audit["duplicate_rows"] == 1
        assert audit["missing_values_per_column"].get("val") == 1
        assert audit["status"] == "WARNING"

    def test_generate_and_save_report(self, tmp_path):
        report_file = tmp_path / "data_quality_report.json"
        datasets = {
            "test_delays": pd.DataFrame([{"train_number": "12002", "historical_delay_minutes": 10.0}]),
            "test_schedules": pd.DataFrame([{"train_number": "12002", "scheduled_arrival": "06:00"}]),
        }

        report = DataValidator.generate_and_save_data_quality_report(datasets, output_file=report_file)
        assert report_file.exists()
        assert report["overall_status"] == "HEALTHY"
        assert "test_delays" in report["audits"]
        assert "test_schedules" in report["audits"]

    def test_out_of_distribution_input_detection(self):
        # Extreme existing delay > 180 min
        ood_request = {
            "request_id": "REQ_OOD_001",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-25",
            "proposed_start_time": "01:30",
            "proposed_end_time": "04:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
            "existing_delay_minutes": 250.0,  # Extreme OOD!
        }

        pred = predict_maintenance_window(ood_request)
        dq = pred["data_quality"]
        assert dq["is_out_of_distribution"] is True
        assert dq["status"] == "OUT_OF_DISTRIBUTION"
        assert any("OOD Warning" in w for w in dq["warnings"])
