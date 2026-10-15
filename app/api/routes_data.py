"""Railway dataset management, catalog, and quality API routes for KAVACH BIE Member 3."""

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.adapters.firebase_auth import get_current_user
from app.config import settings
from app.schemas.datasets import DatasetQualityReportResponse, DatasetRefreshRequest, DatasetSummary
from scripts.discover_datasets import discover_datasets
from scripts.update_datasets import update_datasets
from scripts.validate_datasets import validate_all_datasets

router = APIRouter(prefix="/api/v1/datasets", tags=["Railway Datasets & Pipeline"])


@router.get("", response_model=List[DatasetSummary], status_code=status.HTTP_200_OK)
def list_datasets(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[DatasetSummary]:
    """Retrieve catalog of all ingested and derived railway datasets."""
    cat_file = settings.DATA_METADATA_DIR / "sources_catalog.json"
    if not cat_file.exists():
        discover_datasets()

    with open(cat_file, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    manifest_file = settings.DATA_METADATA_DIR / "download_manifest.json"
    manifest_by_id = {}
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_by_id = {r["dataset_id"]: r for r in json.load(f).get("records", [])}

    prep_file = settings.DATA_METADATA_DIR / "preprocessing_metadata.json"
    prep_by_alias = {}
    if prep_file.exists():
        with open(prep_file, "r", encoding="utf-8") as f:
            prep_by_alias = json.load(f).get("datasets", {})

    summaries = []
    for ds in catalog.get("datasets", []):
        ds_id = ds["dataset_id"]
        m_rec = manifest_by_id.get(ds_id, {})

        key_alias = "stations" if "stations" in ds_id else "trains" if "trains" in ds_id else "schedules" if "schedules" in ds_id else "traffic_density" if ("density" in ds_id or "traffic" in ds_id) else "track_sections"
        p_rec = prep_by_alias.get(key_alias, {})

        size_bytes = p_rec.get("file_size_bytes", m_rec.get("file_size_bytes", 0))

        summaries.append(
            DatasetSummary(
                dataset_id=ds_id,
                name=ds["name"],
                source_organization=ds["source_organization"],
                source_url=ds["source_url"],
                download_url=ds.get("download_url"),
                format=ds["format"],
                license=ds["license"],
                data_classification=ds["data_classification"],
                row_count=p_rec.get("rows"),
                column_count=p_rec.get("columns"),
                file_size_mb=round(size_bytes / (1024 * 1024), 3) if size_bytes else None,
                last_updated_utc=m_rec.get("retrieved_at_utc"),
                sha256=m_rec.get("sha256"),
            )
        )

    return summaries


@router.get("/{dataset_id}/quality", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
def get_dataset_quality(dataset_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Retrieve detailed validation and data quality metrics for a dataset."""
    q_file = settings.DATA_REPORTS_DIR / "data_quality_report.json"
    if not q_file.exists():
        validate_all_datasets()

    with open(q_file, "r", encoding="utf-8") as f:
        report = json.load(f)

    # Search by exact or partial key
    alias_map = {
        "ir_stations_master": "stations",
        "stations": "stations",
        "ir_trains_master": "trains",
        "trains": "trains",
        "ir_schedules_master": "schedules",
        "schedules": "schedules",
        "ir_section_density_derived": "traffic_density",
        "traffic_density": "traffic_density",
    }
    lookup_key = alias_map.get(dataset_id, dataset_id)

    if lookup_key in report.get("datasets", {}):
        return {
            "dataset_id": dataset_id,
            "validated_at": report["validated_at"],
            "overall_status": report["overall_status"],
            "metrics": report["datasets"][lookup_key],
        }

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quality report for dataset '{dataset_id}' not found.")


@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh_datasets(
    payload: DatasetRefreshRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Trigger an incremental or forced update check against remote data repositories."""
    result = update_datasets(dry_run=payload.dry_run, force=payload.force)
    return {
        "status": "COMPLETED",
        "triggered_by": current_user.get("email", "unknown"),
        "result": result,
    }


@router.get("/download/{filename}", status_code=status.HTTP_200_OK)
def download_processed_dataset(filename: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Download a processed CSV file."""
    clean_name = Path(filename).name
    file_path = settings.DATA_PROCESSED_DIR / clean_name

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{clean_name}' not found.")

    return FileResponse(path=file_path, filename=clean_name, media_type="text/csv")
