"""
KAVACH BIE - Member 4: FastAPI web API
======================================

This file only handles web requests. All real checking happens in main.py.

Start the server with:
    python -m uvicorn api:app --reload

Interactive documentation:
    http://127.0.0.1:8000/docs

ACADEMIC DEMONSTRATION ONLY: not approved or certified for real railway use.
"""

from typing import List

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError as FastAPIRequestError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator
import sys
from pathlib import Path

_MEMBER4_DIR = Path(__file__).resolve().parent
if str(_MEMBER4_DIR) not in sys.path:
    sys.path.insert(0, str(_MEMBER4_DIR))

import main

app = FastAPI(
    title="KAVACH BIE - Member 4 Validation API",
    description=(
        "Checks whether a proposed railway maintenance window conflicts with "
        "train movements, duration and resources. Academic demonstration with "
        "synthetic data - not approved or certified for real railway operations."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Which CSV files to use (tests replace this with temporary files)
# ---------------------------------------------------------------------------

def get_data_paths():
    """Return (schedule_csv_path, resources_csv_path)."""
    return main.DEFAULT_SCHEDULE_PATH, main.DEFAULT_RESOURCES_PATH


# ---------------------------------------------------------------------------
# Request model (Pydantic checks the incoming JSON for us)
# ---------------------------------------------------------------------------

class MaintenanceRequest(BaseModel):
    track_section: str
    start_time: str
    end_time: str
    # StrictInt refuses true/false and decimals such as 60.5
    required_duration_minutes: StrictInt = Field(..., gt=0)
    required_resources: List[str] = Field(default_factory=list)

    @field_validator("track_section")
    @classmethod
    def track_section_not_empty(cls, value):
        if not value.strip():
            raise ValueError("track_section must not be empty")
        return value.strip()

    @field_validator("start_time", "end_time")
    @classmethod
    def time_has_correct_format(cls, value, info):
        main.parse_datetime(value, info.field_name)  # raises ValueError if bad
        return value.strip()

    @field_validator("required_resources")
    @classmethod
    def resource_names_not_empty(cls, names):
        for name in names:
            if not name.strip():
                raise ValueError("required_resources must only contain non-empty names")
        return [name.strip() for name in names]

    @model_validator(mode="after")
    def whole_request_is_consistent(self):
        # Re-uses the same rules as main.py (e.g. end time later than start time)
        try:
            main.parse_maintenance_request(self.model_dump())
        except main.InvalidRequestError as error:
            raise ValueError("; ".join(error.errors))
        return self


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(FastAPIRequestError)
async def handle_invalid_request(request: Request, exc: FastAPIRequestError):
    """Return HTTP 422 with short, readable messages."""
    problems = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part != "body"]
        message = str(error.get("msg", "Invalid value"))
        if message.startswith("Value error, "):
            message = message[len("Value error, "):]
        problems.append({"field": ".".join(location) or "request body", "message": message})
    return JSONResponse(status_code=422, content={"status": "INVALID_REQUEST", "errors": problems})


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    """Unexpected bugs become HTTP 500 - never a misleading VALID result."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "INTERNAL_ERROR",
            "detail": "An unexpected internal error occurred. The request was NOT validated.",
        },
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Simple check that the server is running."""
    return {"status": "OK", "module": "KAVACH BIE Member 4 Validation"}


@app.post("/validate")
def validate(request: MaintenanceRequest, paths=Depends(get_data_paths)):
    """
    Validate a proposed maintenance window.

    HTTP 200 -> validation completed (status is VALID or CONFLICT)
    HTTP 422 -> the request was malformed
    HTTP 500 -> a data file is missing/unreadable, or an unexpected error
    """
    schedule_path, resources_path = paths
    try:
        return main.validate_maintenance(request.model_dump(), schedule_path, resources_path)
    except main.DataFileError as error:
        return JSONResponse(
            status_code=500,
            content={"status": "DATA_FILE_ERROR", "detail": str(error)},
        )
