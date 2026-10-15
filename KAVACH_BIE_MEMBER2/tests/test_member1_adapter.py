"""
===============================================================================
Unit Tests: Member 1 Data Ingestion Adapter (adapters/member1_adapter.py)
===============================================================================
Tests schema harmonization, data cleaning, validation, and quality auditing
for Member 1 upstream data handoffs.
"""

import pandas as pd
import pytest

from adapters.member1_adapter import Member1DataAdapter


class TestMember1DataAdapter:
    """Tests for Member 1 ingestion adapter."""

    @pytest.fixture
    def adapter(self, tmp_path):
        return Member1DataAdapter(data_dir=tmp_path)

    def test_harmonize_and_validate_delays_success(self, adapter):
        raw_df = pd.DataFrame(
            [
                {
                    "train_no": "12002",
                    "train_name": "Shatabdi Express",
                    "date": "2026-09-15",
                    "section_code": "SEC_NDLS_CNB",
                    "sch_arr": "06:00",
                    "act_arr": "06:14",
                    "sch_dep": "10:15",
                    "act_dep": "10:31",
                    "delay_mins": 16.0,
                }
            ]
        )

        clean_df, res = adapter.harmonize_and_validate_delays(raw_df, save_to_data_dir=True)
        assert res.is_valid is True
        assert "train_number" in clean_df.columns
        assert "track_section" in clean_df.columns
        assert "historical_delay_minutes" in clean_df.columns
        assert clean_df.loc[0, "historical_delay_minutes"] == 16.0

    def test_harmonize_schedules(self, adapter):
        raw_schedules = pd.DataFrame(
            [
                {
                    "train_no": "12951",
                    "train_name": "Tejas Rajdhani",
                    "src": "MMCT",
                    "dest": "NDLS",
                    "section": "SEC_BCT_ST",
                    "sch_arr": "17:00",
                    "sch_dep": "19:43",
                    "running_time": 163,
                }
            ]
        )

        clean_df, res = adapter.harmonize_and_validate_schedules(raw_schedules)
        assert res.is_valid is True
        assert "destination" in clean_df.columns
        assert "scheduled_running_time_minutes" in clean_df.columns

    def test_audit_incoming_batch(self, adapter):
        delays_df = pd.DataFrame([{"train_number": "12002", "historical_delay_minutes": 10.0}])
        audit = adapter.audit_incoming_batch(delays_df=delays_df)
        assert "delays" in audit
        assert audit["delays"]["total_rows"] == 1
