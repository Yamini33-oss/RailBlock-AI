"""Pydantic schemas for railway maintenance requests."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from optimizer.schemas import MaintenancePriority


class MaintenanceRequestCreate(BaseModel):
    """Schema to submit a new railway maintenance request."""
    request_id: str = Field(..., description="Unique maintenance block request ID (e.g. 'MR-2026-001')")
    track_section_id: str = Field(..., description="Track block section identifier (e.g. 'SEC-NDLS-MTJ')")
    planning_start: str = Field(..., description="ISO datetime string for planning horizon start")
    planning_end: str = Field(..., description="ISO datetime string for planning horizon end")
    required_duration_minutes: int = Field(..., gt=0, description="Required continuous block duration in minutes")
    maintenance_priority: MaintenancePriority = Field(default=MaintenancePriority.MEDIUM)
    required_resources: List[str] = Field(default_factory=list, description="IDs of required work gangs/equipment")
    earliest_start_time: Optional[str] = Field(default=None)
    latest_end_time: Optional[str] = Field(default=None)
    task_dependencies: Optional[List[str]] = Field(default=None)
    existing_approved_blocks: Optional[List[Dict[str, Any]]] = Field(default=None)
    description: Optional[str] = Field(default=None, description="Operational notes or work description")


class MaintenanceRequestResponse(BaseModel):
    """Schema returned when retrieving a maintenance request."""
    request_id: str
    track_section_id: str
    planning_start: str
    planning_end: str
    required_duration_minutes: int
    maintenance_priority: str
    required_resources: List[str]
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
