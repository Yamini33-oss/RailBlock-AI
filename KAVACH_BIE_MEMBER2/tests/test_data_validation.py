"""
===============================================================================
Unit Tests: Data Validation and Quality Assurance (data_validator.py)
===============================================================================
Tests positive and negative validation cases for:
- Historical delays data
- Schedules data
- Traffic density logs
- Single maintenance window requests
"""

import pytest
import pandas as pd
from data_validator import (
    DataValidator,
    calculate_window_span_minutes,
    parse_time_to_minutes,
)


class TestTimeParsingHelpers:
    """Tests for parse_time_to_minutes and calculate_window_span_minutes."""

    def test_parse_valid_times(self):
        assert parse_time_to_minutes("00:00") == 0
        assert parse_time_to_minutes("01:30") == 90
        assert parse_time_to_minutes("12:45") == 765
        assert parse_time_to_minutes("23:59") == 1439
        assert parse_time_to_minutes("06:15:30") == 375

    def test_parse_invalid_times(self):
        assert parse_time_to_minutes("25:00") is None
        assert parse_time_to_minutes("12:65") is None
        assert parse_time_to_minutes("invalid") is None
        assert parse_time_to_minutes(None) is None

    def test_calculate_window_span(self):
        # Same-day span
        assert calculate_window_span_minutes("01:00", "04:00") == 180
        # Overnight rollover
        assert calculate_window_span_minutes("23:00", "02:00") == 180
        # Equal times
        assert calculate_window_span_minutes("05:00", "05:00") == 0


class TestDelaysValidation:
    """Tests for validate_delays_dataframe."""

    @pytest.fixture
    def valid_delays_df(self):
        return pd.DataFrame(
            [
                {
                    "train_number": "12002",
                    "train_name": "Shatabdi Express",
                    "service_date": "2026-09-01",
                    "track_section": "SEC_NDLS_CNB",
                    "scheduled_arrival": "06:00",
                    "actual_arrival": "06:15",
                    "scheduled_departure": "10:15",
                    "actual_departure": "10:30",
                    "historical_delay_minutes": 15.0,
                }
            ]
        )

    def test_valid_delays_pass(self, valid_delays_df):
        res = DataValidator.validate_delays_dataframe(valid_delays_df)
        assert res.is_valid is True
        assert len(res.errors) == 0
        assert len(res.cleaned_df) == 1

    def test_missing_required_columns(self, valid_delays_df):
        bad_df = valid_delays_df.drop(columns=["historical_delay_minutes"])
        res = DataValidator.validate_delays_dataframe(bad_df)
        assert res.is_valid is False
        assert any("Missing required columns" in err for err in res.errors)

    def test_empty_dataframe(self):
        res = DataValidator.validate_delays_dataframe(pd.DataFrame())
        assert res.is_valid is False
        assert any("empty" in err for err in res.errors)

    def test_invalid_date_format(self, valid_delays_df):
        bad_df = valid_delays_df.copy()
        bad_df.loc[0, "service_date"] = "01-09-2026"  # Non-ISO
        res = DataValidator.validate_delays_dataframe(bad_df)
        assert res.is_valid is False
        assert any("invalid service_date" in err for err in res.errors)

    def test_negative_delay_clipping(self, valid_delays_df):
        neg_df = valid_delays_df.copy()
        neg_df.loc[0, "historical_delay_minutes"] = -10.0
        res = DataValidator.validate_delays_dataframe(neg_df)
        assert res.is_valid is True
        assert res.cleaned_df.loc[0, "historical_delay_minutes"] == 0.0
        assert any("negative delay" in w for w in res.warnings)

    def test_duplicate_rows_dropped(self, valid_delays_df):
        dup_df = pd.concat([valid_delays_df, valid_delays_df], ignore_index=True)
        res = DataValidator.validate_delays_dataframe(dup_df)
        assert res.is_valid is True
        assert len(res.cleaned_df) == 1
        assert any("duplicate" in w for w in res.warnings)


class TestSchedulesValidation:
    """Tests for validate_schedules_dataframe."""

    def test_valid_schedules(self):
        df = pd.DataFrame(
            [
                {
                    "train_number": "12951",
                    "train_name": "Tejas Rajdhani",
                    "source": "MMCT",
                    "destination": "NDLS",
                    "track_section": "SEC_BCT_ST",
                    "scheduled_arrival": "17:00",
                    "scheduled_departure": "19:43",
                    "scheduled_running_time_minutes": 163,
                }
            ]
        )
        res = DataValidator.validate_schedules_dataframe(df)
        assert res.is_valid is True
        assert len(res.cleaned_df) == 1

    def test_non_positive_running_time(self):
        df = pd.DataFrame(
            [
                {
                    "train_number": "12951",
                    "train_name": "Tejas Rajdhani",
                    "source": "MMCT",
                    "destination": "NDLS",
                    "track_section": "SEC_BCT_ST",
                    "scheduled_arrival": "17:00",
                    "scheduled_departure": "19:43",
                    "scheduled_running_time_minutes": -20,
                }
            ]
        )
        res = DataValidator.validate_schedules_dataframe(df)
        assert len(res.cleaned_df) == 0


class TestMaintenanceRequestValidation:
    """Tests for validate_single_request."""

    @pytest.fixture
    def valid_request(self):
        return {
            "request_id": "REQ_TEST_001",
            "track_section": "SEC_NDLS_CNB",
            "requested_date": "2026-10-15",
            "proposed_start_time": "01:30",
            "proposed_end_time": "04:30",
            "required_duration_minutes": 180.0,
            "maintenance_priority": "HIGH",
        }

    def test_valid_request_passes(self, valid_request):
        sanitized, warnings = DataValidator.validate_single_request(valid_request)
        assert sanitized["request_id"] == "REQ_TEST_001"
        assert sanitized["required_duration_minutes"] == 180.0
        assert sanitized["maintenance_priority"] == "HIGH"

    def test_missing_required_field_raises(self, valid_request):
        del valid_request["track_section"]
        with pytest.raises(ValueError, match="Missing required maintenance request field"):
            DataValidator.validate_single_request(valid_request)

    def test_negative_duration_raises(self, valid_request):
        valid_request["required_duration_minutes"] = -60.0
        with pytest.raises(ValueError, match="strictly positive"):
            DataValidator.validate_single_request(valid_request)

    def test_excessive_duration_raises(self, valid_request):
        valid_request["required_duration_minutes"] = 1800.0  # 30 hours
        with pytest.raises(ValueError, match="exceeds maximum allowed track possession"):
            DataValidator.validate_single_request(valid_request)

    def test_invalid_date_format_raises(self, valid_request):
        valid_request["requested_date"] = "15-10-2026"
        with pytest.raises(ValueError, match="Invalid date"):
            DataValidator.validate_single_request(valid_request)

    def test_missing_priority_defaults_medium(self, valid_request):
        del valid_request["maintenance_priority"]
        sanitized, warnings = DataValidator.validate_single_request(valid_request)
        assert sanitized["maintenance_priority"] == "MEDIUM"
        assert any("defaulted to 'MEDIUM'" in w for w in warnings)
