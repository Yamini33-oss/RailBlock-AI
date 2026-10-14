"""Pydantic schemas for railway datasets and quality reports."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    """Metadata summary of an ingested railway dataset."""
    dataset_id: str
    name: str
    source_organization: str
    source_url: str
    download_url: Optional[str] = None
    format: str
    license: str
    data_classification: str
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    file_size_mb: Optional[float] = None
    last_updated_utc: Optional[str] = None
    sha256: Optional[str] = None


class DatasetQualityReportResponse(BaseModel):
    """Quality report for a specific dataset or the entire pipeline."""
    validation_version: str
    validated_at: str
    overall_status: str
    dataset_details: Dict[str, Any]


class DatasetRefreshRequest(BaseModel):
    """Trigger an on-demand update check for railway datasets."""
    dry_run: bool = False
    force: bool = False
