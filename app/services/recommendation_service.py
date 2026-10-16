
"""Recommendation and optimization job execution service for KAVACH BIE Member 3.

Coordinates:
- Loading processed railway schedules and traffic density
- Formulating maintenance requests
- Running OR-Tools maintenance-window optimization
- Predicting disruption through Member 2's HTTP API
- Validating candidates through Member 4's HTTP API
- Persisting jobs and results in Cloud Firestore
- Dispatching push alerts via Firebase Cloud Messaging
- Auditing user actions

Academic demonstration using real or synthetic datasets.
Not certified for real railway operations.
"""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import pandas as pd

from app.adapters.fcm_notifier import fcm_notifier
from app.adapters.firestore_repository import firestore_repo
from app.config import settings
from app.schemas.optimization import OptimizationJobCreate
from optimizer.data_adapter import (
    DataLoader,
    Member2PredictorAdapter,
    normalize_datetime,
)
from optimizer.member2_client import predict_candidate_window
from optimizer.schemas import (
    MaintenancePriority,
    MaintenanceRequest,
    PlanningConfig,
    TrafficDensityRecord,
    TrainSchedule,
)
from optimizer.service import optimize_maintenance_window
from optimizer.validation_client import Member4HTTPClient

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service orchestrating optimization, prediction, and validation."""

    def __init__(self) -> None:
        self.default_tz = ZoneInfo(settings.DEFAULT_TIMEZONE)

    def load_real_schedule_data_for_section(
        self,
        track_section_id: str,
        planning_start: datetime,
        planning_end: datetime,
    ) -> List[TrainSchedule]:
        """Load train movements associated with a track section."""

        sec_file = (
            settings.DATA_PROCESSED_DIR / "track_sections_processed.csv"
        )
        sched_file = (
            settings.DATA_PROCESSED_DIR / "schedules_processed.csv"
        )

        if not (sec_file.exists() and sched_file.exists()):
            logger.warning(
                "Processed railway data not found; "
                "falling back to synthetic schedules."
            )
            synth_file = settings.DATA_SYNTHETIC_DIR / "train_schedule.csv"
            return (
                DataLoader.load_train_schedules(synth_file)
                if synth_file.exists()
                else []
            )

        sec_df = pd.read_csv(sec_file)
        sec_match = sec_df[
            sec_df["track_section_id"] == track_section_id
        ]

        if sec_match.empty:
            target_codes = {"NDLS", "MTJ", "AGC"}
            logger.warning(
                "Track section %s not found in processed section data; "
                "using fallback station codes.",
                track_section_id,
            )
        else:
            row = sec_match.iloc[0]
            target_codes = {
                str(row["from_station_code"]).strip().upper(),
                str(row["to_station_code"]).strip().upper(),
            }

        sched_df = pd.read_csv(sched_file)
        rel_sched = sched_df[
            sched_df["station_code"]
            .astype(str)
            .str.upper()
            .isin(target_codes)
        ]

        if rel_sched.empty:
            logger.warning(
                "No matching station schedules found for %s; "
                "using fallback rows.",
                track_section_id,
            )
            rel_sched = sched_df.head(200)

        train_schedules: List[TrainSchedule] = []
        base_date = planning_start.date()

        for _, srow in rel_sched.head(60).iterrows():
            try:
                t_arr_str = str(srow["arrival_time"]).strip()
                t_dep_str = str(srow["departure_time"]).strip()

                if not t_arr_str or t_arr_str.lower() in {"none", "nan"}:
                    t_arr_str = t_dep_str
                if not t_dep_str or t_dep_str.lower() in {"none", "nan"}:
                    t_dep_str = t_arr_str

                arr_parts = [int(x) for x in t_arr_str.split(":")]
                dep_parts = [int(x) for x in t_dep_str.split(":")]

                h_arr, m_arr = arr_parts[0], arr_parts[1]
                s_arr = arr_parts[2] if len(arr_parts) > 2 else 0

                h_dep, m_dep = dep_parts[0], dep_parts[1]
                s_dep = dep_parts[2] if len(dep_parts) > 2 else 0

                arr_dt = datetime(
                    base_date.year,
                    base_date.month,
                    base_date.day,
                    h_arr,
                    m_arr,
                    s_arr,
                    tzinfo=self.default_tz,
                )
                dep_dt = datetime(
                    base_date.year,
                    base_date.month,
                    base_date.day,
                    h_dep,
                    m_dep,
                    s_dep,
                    tzinfo=self.default_tz,
                )

                # Handle overnight train movements.
                if dep_dt < arr_dt:
                    dep_dt += timedelta(days=1)

                # Keep movements overlapping the planning horizon.
                if dep_dt < planning_start or arr_dt > planning_end:
                    continue

                train_schedules.append(
                    TrainSchedule(
                        train_number=str(srow["train_number"]).zfill(5),
                        train_name=str(srow.get("train_name", "Express")),
                        track_section_id=track_section_id,
                        scheduled_arrival=arr_dt,
                        scheduled_departure=dep_dt,
                        train_type="EXPRESS",
                        priority_weight=1.2,
                    )
                )

            except (KeyError, TypeError, ValueError, IndexError) as exc:
                logger.debug("Skipping invalid schedule row: %s", exc)
                continue

        logger.info(
            "Loaded %d schedule records for section %s",
            len(train_schedules),
            track_section_id,
        )
        return train_schedules

    def load_real_traffic_density_for_section(
        self,
        track_section_id: str,
        planning_start: datetime,
        planning_end: datetime,
    ) -> List[TrafficDensityRecord]:
        """Load hourly traffic-density records for a track section."""

        dens_file = (
            settings.DATA_PROCESSED_DIR
            / "section_traffic_density_processed.csv"
        )

        if not dens_file.exists():
            logger.warning(
                "Processed traffic-density data not found; "
                "using synthetic data."
            )
            synth_file = settings.DATA_SYNTHETIC_DIR / "traffic_density.csv"
            return (
                DataLoader.load_traffic_density(synth_file)
                if synth_file.exists()
                else []
            )

        df = pd.read_csv(dens_file)
        sec_df = df[df["track_section_id"] == track_section_id]

        if sec_df.empty:
            logger.warning(
                "No traffic-density records found for %s; "
                "using fallback records.",
                track_section_id,
            )
            sec_df = df.head(24)

        records: List[TrafficDensityRecord] = []
        current_hour = planning_start.replace(
            minute=0, second=0, microsecond=0
        )

        while current_hour < planning_end:
            hour = current_hour.hour
            hour_rows = sec_df[sec_df["hour_of_day"] == hour]

            if not hour_rows.empty:
                row = hour_rows.iloc[0]
                interval_end = min(
                    current_hour + timedelta(hours=1),
                    planning_end,
                )

                records.append(
                    TrafficDensityRecord(
                        track_section_id=track_section_id,
                        start_time=current_hour,
                        end_time=interval_end,
                        density_score=float(row["traffic_density_score"]),
                        density_category=str(
                            row["density_category"]
                        ).upper(),
                    )
                )

            current_hour += timedelta(hours=1)

        return records

    def run_optimization_job(
        self,
        job_request: OptimizationJobCreate,
        current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an optimization job, validate candidates, and persist results."""

        job_id = f"job-{uuid.uuid4().hex[:10]}"
        request_id = job_request.request_id

        # 1. Fetch the maintenance request.
        req_doc = firestore_repo.get_maintenance_request(request_id)

        if not req_doc:
            synth_reqs = (
                settings.DATA_SYNTHETIC_DIR / "maintenance_requests.csv"
            )

            if synth_reqs.exists():
                df_reqs = pd.read_csv(synth_reqs)
                match = df_reqs[df_reqs["request_id"] == request_id]

                if not match.empty:
                    rrow = match.iloc[0].to_dict()
                    raw_resources = rrow.get("required_resources")

                    if (
                        raw_resources is not None
                        and pd.notna(raw_resources)
                        and str(raw_resources).strip()
                    ):
                        required_resources = [str(raw_resources).strip()]
                    else:
                        required_resources = []

                    req_doc = {
                        "request_id": request_id,
                        "track_section_id": rrow["track_section_id"],
                        "planning_start": rrow["planning_start"],
                        "planning_end": rrow["planning_end"],
                        "required_duration_minutes": int(
                            rrow["required_duration_minutes"]
                        ),
                        "maintenance_priority": rrow.get(
                            "maintenance_priority", "MEDIUM"
                        ),
                        "required_resources": required_resources,
                    }
                    firestore_repo.save_maintenance_request(
                        request_id, req_doc
                    )

        if not req_doc:
            raise ValueError(
                f"Maintenance request '{request_id}' "
                "not found in database or catalogs."
            )

        # 2. Register the optimization job.
        firestore_repo.create_optimization_job(
            job_id,
            request_id,
            job_request.model_dump(mode="json"),
        )
        firestore_repo.update_optimization_job(
            job_id,
            status="RUNNING",
        )

        # 3. Formulate the maintenance request.
        p_start = normalize_datetime(
            req_doc["planning_start"], self.default_tz
        )
        p_end = normalize_datetime(
            req_doc["planning_end"], self.default_tz
        )

        raw_resources = req_doc.get("required_resources", [])

        if isinstance(raw_resources, str):
            raw_resources = (
                [raw_resources] if raw_resources.strip() else []
            )

        mreq = MaintenanceRequest(
            request_id=request_id,
            track_section_id=req_doc["track_section_id"],
            planning_start=p_start,
            planning_end=p_end,
            required_duration_minutes=req_doc[
                "required_duration_minutes"
            ],
            maintenance_priority=MaintenancePriority(
                str(
                    getattr(
                        req_doc.get("maintenance_priority", "MEDIUM"),
                        "value",
                        req_doc.get("maintenance_priority", "MEDIUM"),
                    )
                ).upper()
            ),
            required_resources=raw_resources or [],
            earliest_start_time=(
                normalize_datetime(
                    req_doc["earliest_start_time"], self.default_tz
                )
                if req_doc.get("earliest_start_time")
                else None
            ),
            latest_end_time=(
                normalize_datetime(
                    req_doc["latest_end_time"], self.default_tz
                )
                if req_doc.get("latest_end_time")
                else None
            ),
        )

        # 4. Load schedule and traffic datasets.
        if job_request.use_real_datasets:
            train_data = self.load_real_schedule_data_for_section(
                mreq.track_section_id,
                p_start,
                p_end,
            )
            traffic_data = self.load_real_traffic_density_for_section(
                mreq.track_section_id,
                p_start,
                p_end,
            )
        else:
            train_source = (
                job_request.custom_train_data
                or settings.DATA_SYNTHETIC_DIR / "train_schedule.csv"
            )
            traffic_source = (
                job_request.custom_traffic_data
                or settings.DATA_SYNTHETIC_DIR / "traffic_density.csv"
            )

            train_data = DataLoader.load_train_schedules(train_source)
            traffic_data = DataLoader.load_traffic_density(traffic_source)

        # 5. Load resource calendars.
        res_file = (
            settings.DATA_SYNTHETIC_DIR / "resource_availability.csv"
        )
        resource_data = (
            DataLoader.load_resource_availability(res_file)
            if res_file.exists()
            else []
        )

        if not resource_data:
            logger.warning(
                "Resource availability calendar is missing or empty. "
                "The optimizer may reject candidates whose resources "
                "cannot be verified."
            )

        # 6. Configure Member 4 validation.
        member4_base_url = getattr(
            settings,
            "MEMBER4_BASE_URL",
            "http://127.0.0.1:8004",
        )

        validator = Member4HTTPClient(
            base_url=member4_base_url,
            required_resources=(
                mreq.required_resources or ["Maintenance Team"]
            ),
        )

        # 7. Configure Member 2 prediction.
        member2_url = os.getenv(
            "MEMBER2_PREDICTION_URL",
            "http://127.0.0.1:8005/predict",
        )

        priority_value = getattr(
            mreq.maintenance_priority,
            "value",
            str(mreq.maintenance_priority),
        )

        def member2_predictor(
            candidate_window,
            candidate_train_data,
            candidate_traffic_data,
        ):
            # Use the endpoint configured for this running service.
            # The client reads the same environment variable.
            return predict_candidate_window(
                candidate_window,
                candidate_train_data,
                candidate_traffic_data,
                maintenance_priority=priority_value,
            )

        predictor = Member2PredictorAdapter(
            predictor_callable=member2_predictor,
            fallback_to_baseline=False,
        )

        logger.info(
            "Member 2 prediction endpoint configured: %s",
            member2_url,
        )

        # 8. Run optimization with Member 2 predictions and Member 4 validation.
        config = job_request.config or PlanningConfig()

        opt_response = optimize_maintenance_window(
            request=mreq,
            input_data={
                "train_data": train_data,
                "traffic_data": traffic_data,
                "resource_data": resource_data,
            },
            config=config,
            predictor=predictor,
            validator=validator,
        )

        # 9. Save the optimization result.
        result_dict = opt_response.model_dump(mode="json")
        firestore_repo.save_optimization_result(
            job_id,
            result_dict,
        )
        firestore_repo.update_optimization_job(
            job_id,
            status="COMPLETED",
            result_id=job_id,
        )

        # 10. Audit the outcome.
        firestore_repo.log_audit_event(
            user_id=current_user.get("uid", "anonymous"),
            action="OPTIMIZATION_JOB_COMPLETED",
            details={
                "job_id": job_id,
                "request_id": request_id,
                "status": opt_response.status.value,
                "recommended_start": (
                    opt_response.recommendation.start_time.isoformat()
                    if opt_response.recommendation
                    else None
                ),
            },
        )

        # 11. Notify subscribers.
        fcm_notifier.send_notification(
            title=f"Maintenance Block Solved: {request_id}",
            body=(
                f"Status: {opt_response.status.value}. "
                "Recommendation ready for review."
            ),
            data={
                "job_id": job_id,
                "request_id": request_id,
                "status": opt_response.status.value,
            },
            topic="maintenance_dispatch",
        )

        now = datetime.now(timezone.utc).isoformat()

        return {
            "job_id": job_id,
            "request_id": request_id,
            "status": "COMPLETED",
            "created_at": now,
            "updated_at": now,
            "result": opt_response,
        }


recommendation_service = RecommendationService()
