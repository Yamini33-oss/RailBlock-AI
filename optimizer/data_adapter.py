"""Data adapters and external service interfaces for KAVACH BIE Member 3.

Handles ingestion, normalization, and validation of train schedules,
traffic density data, resource calendars, and section availability.
Provides a pluggable interface for Member 2's delay/disruption predictor.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

import pandas as pd
from dateutil import parser as date_parser

from optimizer.exceptions import DataValidationError, PredictionServiceError
from optimizer.schemas import (
    CandidateWindow,
    DisruptionPrediction,
    MaintenancePriority,
    MaintenanceRequest,
    ResourceAvailabilityRecord,
    SectionAvailabilityRecord,
    TrafficDensityCategory,
    TrafficDensityRecord,
    TrainSchedule,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = ZoneInfo("Asia/Kolkata")


def normalize_datetime(dt_val: Any, default_tz: ZoneInfo = DEFAULT_TIMEZONE) -> datetime:
    """Normalize input into an aware datetime object in the default timezone."""
    if isinstance(dt_val, str):
        dt = date_parser.parse(dt_val)
    elif isinstance(dt_val, datetime):
        dt = dt_val
    elif hasattr(dt_val, "to_pydatetime"):
        dt = dt_val.to_pydatetime()
    else:
        raise DataValidationError(f"Cannot parse datetime from: {dt_val!r}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt


# ---------------------------------------------------------------------------
# Member 2 Delay/Disruption Prediction Protocol and Adapters
# ---------------------------------------------------------------------------

class DelayPredictorInterface(ABC):
    """Abstract interface for delay/disruption prediction services (Member 2)."""

    @abstractmethod
    def predict_disruption(
        self,
        candidate_window: CandidateWindow,
        train_data: List[TrainSchedule],
        traffic_data: List[TrafficDensityRecord],
    ) -> DisruptionPrediction:
        """Estimate the delay and network disruption caused by a candidate window."""
        pass


class BaselineDelayPredictor(DelayPredictorInterface):
    """Explicitly labeled baseline heuristic predictor for development, demo, and testing.

    Uses train count, train types, priorities, and local traffic density to estimate
    operational delay in minutes. Clearly marked as synthetic to avoid confusion with
    Member 2's machine learning model.
    """

    def __init__(self, model_version: str = "baseline-heuristic-v1 (synthetic demo)") -> None:
        self.model_version = model_version

    def predict_disruption(
        self,
        candidate_window: CandidateWindow,
        train_data: List[TrainSchedule],
        traffic_data: List[TrafficDensityRecord],
    ) -> DisruptionPrediction:
        # 1. Identify overlapping trains on the same track section
        overlapping_trains: List[TrainSchedule] = []
        for train in train_data:
            if train.track_section_id == candidate_window.track_section_id:
                # Overlap test: max(start1, start2) < min(end1, end2)
                overlap_start = max(train.scheduled_arrival, candidate_window.start_time)
                overlap_end = min(train.scheduled_departure, candidate_window.end_time)
                if overlap_start < overlap_end:
                    overlapping_trains.append(train)

        # 2. Base delay per train category
        type_delay_map = {
            "RAJDHANI": 40.0,
            "EXPRESS": 30.0,
            "PASSENGER": 20.0,
            "FREIGHT": 25.0,
        }

        total_delay = 0.0
        for tr in overlapping_trains:
            tr_type = (tr.train_type or "PASSENGER").upper()
            base = type_delay_map.get(tr_type, 20.0)
            total_delay += base * tr.priority_weight

        # 3. Density multiplier
        # Average density for this window
        relevant_densities = [
            td.density_score
            for td in traffic_data
            if td.track_section_id == candidate_window.track_section_id
            and max(td.start_time, candidate_window.start_time) < min(td.end_time, candidate_window.end_time)
        ]
        avg_density = sum(relevant_densities) / len(relevant_densities) if relevant_densities else 0.5

        # Higher traffic density exacerbates secondary delay
        density_multiplier = 1.0 + (avg_density * 1.5)
        predicted_delay = total_delay * density_multiplier

        # Add small duration factor: longer blocks cause slight dispersion delays
        duration_factor = (candidate_window.duration_minutes / 60.0) * 2.0
        if overlapping_trains:
            predicted_delay += duration_factor
        else:
            # When zero trains overlap, disruption is minimal baseline clearance time
            predicted_delay = min(avg_density * 3.0, 5.0)

        return DisruptionPrediction(
            candidate_id=candidate_window.candidate_id,
            predicted_delay_minutes=round(predicted_delay, 2),
            confidence=0.85,
            model_version=self.model_version,
            details={
                "overlapping_train_count": len(overlapping_trains),
                "avg_traffic_density": round(avg_density, 3),
                "density_multiplier": round(density_multiplier, 3),
            },
        )


class Member2PredictorAdapter(DelayPredictorInterface):
    """Adapter connecting to Member 2's prediction engine or callable."""

    def __init__(
        self,
        predictor_callable: Optional[Callable[..., Any]] = None,
        fallback_to_baseline: bool = False,
    ) -> None:
        self.predictor_callable = predictor_callable
        self.fallback_to_baseline = fallback_to_baseline
        self._baseline = BaselineDelayPredictor(model_version="baseline-fallback-v1")

    def predict_disruption(
        self,
        candidate_window: CandidateWindow,
        train_data: List[TrainSchedule],
        traffic_data: List[TrafficDensityRecord],
    ) -> DisruptionPrediction:
        if self.predictor_callable is None:
            if self.fallback_to_baseline:
                logger.warning(
                    "Member 2 predictor callable not supplied; falling back to BaselineDelayPredictor."
                )
                return self._baseline.predict_disruption(candidate_window, train_data, traffic_data)
            raise PredictionServiceError(
                "Member 2 delay prediction service is not configured or unavailable.",
                details={"candidate_id": candidate_window.candidate_id},
            )

        try:
            result = self.predictor_callable(candidate_window, train_data, traffic_data)
            if isinstance(result, DisruptionPrediction):
                return result
            if isinstance(result, dict):
                return DisruptionPrediction(
                    candidate_id=candidate_window.candidate_id,
                    predicted_delay_minutes=float(result.get("predicted_delay_minutes", 0.0)),
                    confidence=float(result.get("confidence", 1.0)),
                    model_version=str(result.get("model_version", "member2-model")),
                    details=result.get("details", {}),
                )
            if isinstance(result, (int, float)):
                return DisruptionPrediction(
                    candidate_id=candidate_window.candidate_id,
                    predicted_delay_minutes=float(result),
                    confidence=1.0,
                    model_version="member2-direct-callable",
                )
            raise PredictionServiceError(f"Unexpected return type from Member 2 predictor: {type(result)}")
        except Exception as exc:
            logger.error("Member 2 prediction failed for candidate %s: %s", candidate_window.candidate_id, exc)
            if self.fallback_to_baseline:
                logger.warning("Falling back to BaselineDelayPredictor due to Member 2 failure.")
                return self._baseline.predict_disruption(candidate_window, train_data, traffic_data)
            raise PredictionServiceError(
                f"Member 2 delay prediction service failed: {exc}",
                details={"candidate_id": candidate_window.candidate_id, "original_error": str(exc)},
            ) from exc


# ---------------------------------------------------------------------------
# Data Loaders (CSV, DataFrame, Dict)
# ---------------------------------------------------------------------------

class DataLoader:
    """Utility class to parse and validate CSV or DataFrame datasets into typed records."""

    @staticmethod
    def load_train_schedules(
        source: Union[str, Path, pd.DataFrame, List[Any]],
        default_tz: ZoneInfo = DEFAULT_TIMEZONE,
    ) -> List[TrainSchedule]:
        """Load and validate train schedules."""
        if isinstance(source, list):
            if len(source) == 0:
                return []
            if isinstance(source[0], TrainSchedule):
                return source
            df = pd.DataFrame(source)
        elif isinstance(source, (str, Path)):
            p = Path(source)
            if not p.exists():
                raise DataValidationError(f"Train schedule file does not exist: {p}")
            df = pd.read_csv(p)
        elif isinstance(source, pd.DataFrame):
            df = source.copy()
        else:
            raise DataValidationError(f"Unsupported data source type for train schedules: {type(source)}")

        if df.empty:
            return []

        required_cols = {"train_number", "track_section_id", "scheduled_arrival", "scheduled_departure"}
        missing = required_cols - set(df.columns)
        if missing:
            raise DataValidationError(f"Train schedule data missing required columns: {missing}")

        schedules: List[TrainSchedule] = []
        for idx, row in df.iterrows():
            try:
                arr = normalize_datetime(row["scheduled_arrival"], default_tz)
                dep = normalize_datetime(row["scheduled_departure"], default_tz)
                # If departure is earlier than arrival (e.g. crossing midnight or typo in input)
                if dep < arr:
                    # In railway operations, trains traversing overnight exit later
                    dep = dep.replace(day=dep.day + 1)

                rec = TrainSchedule(
                    train_number=str(row["train_number"]).strip(),
                    train_name=str(row.get("train_name", "")).strip() if pd.notna(row.get("train_name")) else None,
                    source=str(row.get("source", "")).strip() if pd.notna(row.get("source")) else None,
                    destination=str(row.get("destination", "")).strip() if pd.notna(row.get("destination")) else None,
                    track_section_id=str(row["track_section_id"]).strip(),
                    scheduled_arrival=arr,
                    scheduled_departure=dep,
                    train_type=str(row.get("train_type", "PASSENGER")).strip() if pd.notna(row.get("train_type")) else "PASSENGER",
                    priority_weight=float(row.get("priority_weight", 1.0)) if pd.notna(row.get("priority_weight")) else 1.0,
                )
                schedules.append(rec)
            except Exception as e:
                raise DataValidationError(f"Invalid train schedule row at index {idx}: {e}") from e

        return schedules

    @staticmethod
    def load_traffic_density(
        source: Union[str, Path, pd.DataFrame, List[Any]],
        default_tz: ZoneInfo = DEFAULT_TIMEZONE,
    ) -> List[TrafficDensityRecord]:
        """Load and validate traffic density records."""
        if isinstance(source, list):
            if len(source) == 0:
                return []
            if isinstance(source[0], TrafficDensityRecord):
                return source
            df = pd.DataFrame(source)
        elif isinstance(source, (str, Path)):
            p = Path(source)
            if not p.exists():
                raise DataValidationError(f"Traffic density file does not exist: {p}")
            df = pd.read_csv(p)
        elif isinstance(source, pd.DataFrame):
            df = source.copy()
        else:
            raise DataValidationError(f"Unsupported data source type for traffic density: {type(source)}")

        if df.empty:
            return []

        required_cols = {"track_section_id", "start_time", "end_time", "density_score"}
        missing = required_cols - set(df.columns)
        if missing:
            raise DataValidationError(f"Traffic density data missing required columns: {missing}")

        records: List[TrafficDensityRecord] = []
        for idx, row in df.iterrows():
            try:
                start = normalize_datetime(row["start_time"], default_tz)
                end = normalize_datetime(row["end_time"], default_tz)
                cat_str = str(row.get("density_category", "MEDIUM")).upper()
                cat = TrafficDensityCategory(cat_str) if cat_str in TrafficDensityCategory.__members__ else TrafficDensityCategory.MEDIUM

                rec = TrafficDensityRecord(
                    track_section_id=str(row["track_section_id"]).strip(),
                    start_time=start,
                    end_time=end,
                    density_score=float(row["density_score"]),
                    density_category=cat,
                )
                records.append(rec)
            except Exception as e:
                raise DataValidationError(f"Invalid traffic density row at index {idx}: {e}") from e

        return records

    @staticmethod
    def load_resource_availability(
        source: Union[str, Path, pd.DataFrame, List[Any]],
        default_tz: ZoneInfo = DEFAULT_TIMEZONE,
    ) -> List[ResourceAvailabilityRecord]:
        """Load and validate resource availability records."""
        if isinstance(source, list):
            if len(source) == 0:
                return []
            if isinstance(source[0], ResourceAvailabilityRecord):
                return source
            df = pd.DataFrame(source)
        elif isinstance(source, (str, Path)):
            p = Path(source)
            if not p.exists():
                return []
            df = pd.read_csv(p)
        elif isinstance(source, pd.DataFrame):
            df = source.copy()
        else:
            return []

        if df.empty:
            return []

        required_cols = {"resource_id", "available_start", "available_end"}
        if not required_cols.issubset(set(df.columns)):
            return []

        records: List[ResourceAvailabilityRecord] = []
        for idx, row in df.iterrows():
            try:
                start = normalize_datetime(row["available_start"], default_tz)
                end = normalize_datetime(row["available_end"], default_tz)
                rec = ResourceAvailabilityRecord(
                    resource_id=str(row["resource_id"]).strip(),
                    resource_name=str(row.get("resource_name", "")).strip() if pd.notna(row.get("resource_name")) else None,
                    available_start=start,
                    available_end=end,
                    quantity_available=int(row.get("quantity_available", 1)),
                )
                records.append(rec)
            except Exception as e:
                logger.warning("Skipping invalid resource row %s: %s", idx, e)

        return records

    @staticmethod
    def load_section_availability(
        source: Union[str, Path, pd.DataFrame, List[Any]],
        default_tz: ZoneInfo = DEFAULT_TIMEZONE,
    ) -> List[SectionAvailabilityRecord]:
        """Load and validate section availability records."""
        if isinstance(source, list):
            if len(source) == 0:
                return []
            if isinstance(source[0], SectionAvailabilityRecord):
                return source
            df = pd.DataFrame(source)
        elif isinstance(source, (str, Path)):
            p = Path(source)
            if not p.exists():
                return []
            df = pd.read_csv(p)
        elif isinstance(source, pd.DataFrame):
            df = source.copy()
        else:
            return []

        if df.empty:
            return []

        required_cols = {"track_section_id", "available_start", "available_end"}
        if not required_cols.issubset(set(df.columns)):
            return []

        records: List[SectionAvailabilityRecord] = []
        for idx, row in df.iterrows():
            try:
                start = normalize_datetime(row["available_start"], default_tz)
                end = normalize_datetime(row["available_end"], default_tz)
                rec = SectionAvailabilityRecord(
                    track_section_id=str(row["track_section_id"]).strip(),
                    available_start=start,
                    available_end=end,
                    is_blocked=bool(row.get("is_blocked", False)),
                    block_reason=str(row.get("block_reason", "")).strip() if pd.notna(row.get("block_reason")) else None,
                )
                records.append(rec)
            except Exception as e:
                logger.warning("Skipping invalid section availability row %s: %s", idx, e)

        return records
