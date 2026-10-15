"""
KAVACH BIE - Member 4: Conflict Detection and Operational Validation
=====================================================================

This file holds ALL of the validation logic. It only uses Python's standard
library, so you can read it and run it without installing anything.

The web API (api.py) is a thin wrapper around the function
`validate_maintenance()` at the bottom of this file.

ACADEMIC DEMONSTRATION ONLY: this is not an approved, certified or safe
system for real railway operations. The data files contain synthetic data.

You can try the logic directly from a terminal:
    python main.py
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# Folder that contains this file. Using it means the CSV files are found even
# if the terminal is opened in a different folder. No computer-specific paths!
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SCHEDULE_PATH = BASE_DIR / "train_schedule.csv"
DEFAULT_RESOURCES_PATH = BASE_DIR / "resources.csv"

# The ONE date/time format used everywhere in this project.
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
_DATETIME_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$")

SCHEDULE_COLUMNS = ["train_id", "train_name", "track_section", "start_time", "end_time"]
RESOURCE_COLUMNS = ["resource_name", "available"]

# Accepted spellings for the "available" column (not case sensitive).
TRUE_VALUES = {"true", "yes", "y", "1"}
FALSE_VALUES = {"false", "no", "n", "0"}

ACADEMIC_NOTE = (
    "Academic demonstration using synthetic data. "
    "Not approved or certified for real railway operations."
)


# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------

class DataFileError(Exception):
    """A CSV file is missing, unreadable, empty, or lacks required columns."""


class InvalidRequestError(Exception):
    """The maintenance request itself is invalid. `errors` lists every problem."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# ---------------------------------------------------------------------------
# 1. Loading CSV files
# ---------------------------------------------------------------------------

def load_csv_file(path, required_columns):
    """
    Read a CSV file and return a list of (line_number, row_dictionary).

    Raises DataFileError if the file is missing, unreadable, empty, or does
    not contain every required column. Completely blank lines are skipped.
    Rows with the wrong number of cells get a "__problem__" entry so that
    the validators below can report them instead of trusting them.
    """
    path = Path(path)
    if not path.is_file():
        raise DataFileError(f"CSV file not found: {path.name} (looked in {path.parent})")

    rows = []
    try:
        # utf-8-sig also handles files saved by Excel with a hidden BOM mark.
        with open(path, newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader, None)
            if header is None:
                raise DataFileError(f"CSV file {path.name} is empty (no header row)")

            header = [name.strip() for name in header]
            missing = [column for column in required_columns if column not in header]
            if missing:
                raise DataFileError(
                    f"CSV file {path.name} is missing required column(s): {', '.join(missing)}"
                )

            for cells in reader:
                if not any(cell.strip() for cell in cells):
                    continue  # skip blank lines
                record = {}
                for position, name in enumerate(header):
                    record[name] = cells[position].strip() if position < len(cells) else ""
                if len(cells) != len(header):
                    record["__problem__"] = (
                        f"expected {len(header)} columns but found {len(cells)}"
                    )
                rows.append((reader.line_num, record))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise DataFileError(f"Could not read CSV file {path.name}: {error}") from error

    return rows


# ---------------------------------------------------------------------------
# 2. Parsing date/time values
# ---------------------------------------------------------------------------

def parse_datetime(value, field_name="time"):
    """
    Convert text like '2026-10-15 13:15' into a datetime.
    Raises ValueError with a readable message if the text is not valid.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text in the format YYYY-MM-DD HH:MM")
    text = value.strip()
    if not _DATETIME_PATTERN.match(text):
        raise ValueError(f"{field_name} '{value}' is not in the format YYYY-MM-DD HH:MM")
    try:
        return datetime.strptime(text, DATETIME_FORMAT)
    except ValueError:
        raise ValueError(f"{field_name} '{value}' is not a real calendar date and time") from None


def format_datetime(moment):
    """Turn a datetime back into text (so JSON responses never hold datetimes)."""
    return moment.strftime(DATETIME_FORMAT)


# ---------------------------------------------------------------------------
# 3. Validating the maintenance request
# ---------------------------------------------------------------------------

def parse_maintenance_request(data):
    """
    Check a maintenance request (a dictionary) and return a cleaned dictionary
    that contains real datetime objects.

    Raises InvalidRequestError listing ALL problems found. Nothing is silently
    replaced with a default value (except an omitted resource list, which
    simply means "no resources required").
    """
    if not isinstance(data, dict):
        raise InvalidRequestError(["The request must be an object with named fields"])

    errors = []

    # --- track section ---
    track_section = data.get("track_section")
    if not isinstance(track_section, str) or not track_section.strip():
        errors.append("track_section is required and must not be empty")
        track_section = ""
    track_section = track_section.strip()

    # --- start and end times ---
    start = end = None
    try:
        start = parse_datetime(data.get("start_time"), "start_time")
    except ValueError as error:
        errors.append(str(error))
    try:
        end = parse_datetime(data.get("end_time"), "end_time")
    except ValueError as error:
        errors.append(str(error))
    if start is not None and end is not None and end <= start:
        errors.append("end_time must be later than start_time")

    # --- duration: must be a real whole number (True/False and 60.5 are rejected) ---
    duration = data.get("required_duration_minutes")
    if isinstance(duration, bool) or not isinstance(duration, int):
        errors.append("required_duration_minutes is required and must be a whole number")
    elif duration <= 0:
        errors.append("required_duration_minutes must be greater than zero")

    # --- resources ---
    resources = data.get("required_resources", [])
    if not isinstance(resources, list):
        errors.append("required_resources must be a list of resource names")
        resources = []
    cleaned_resources = []
    for name in resources:
        if not isinstance(name, str) or not name.strip():
            errors.append("required_resources must only contain non-empty names")
            break
        if name.strip() not in cleaned_resources:  # ignore exact duplicates
            cleaned_resources.append(name.strip())

    if errors:
        raise InvalidRequestError(errors)

    return {
        "track_section": track_section,
        "start": start,
        "end": end,
        "required_duration_minutes": duration,
        "required_resources": cleaned_resources,
    }


# ---------------------------------------------------------------------------
# 4. Validating the train schedule data
# ---------------------------------------------------------------------------

def validate_schedule_rows(rows):
    """
    Split schedule rows into valid trains and invalid records.

    Returns (valid_trains, invalid_records).
    Each invalid record says which CSV line is wrong and why.
    """
    valid_trains = []
    invalid_records = []

    for line_number, row in rows:
        problems = []
        if "__problem__" in row:
            problems.append(row["__problem__"])

        train_id = row.get("train_id", "")
        track_section = row.get("track_section", "")
        if not train_id:
            problems.append("train_id is empty")
        if not track_section:
            problems.append("track_section is empty")

        start = end = None
        try:
            start = parse_datetime(row.get("start_time", ""), "start_time")
        except ValueError as error:
            problems.append(str(error))
        try:
            end = parse_datetime(row.get("end_time", ""), "end_time")
        except ValueError as error:
            problems.append(str(error))
        if start is not None and end is not None and end <= start:
            problems.append("end_time is not later than start_time")

        if problems:
            invalid_records.append({
                "line_number": line_number,
                "train_id": train_id,
                "problems": problems,
            })
        else:
            valid_trains.append({
                "train_id": train_id,
                "train_name": row.get("train_name", ""),
                "track_section": track_section,
                "start": start,
                "end": end,
            })

    return valid_trains, invalid_records


# ---------------------------------------------------------------------------
# 5. Finding trains and detecting overlaps
# ---------------------------------------------------------------------------

def same_section(section_a, section_b):
    """Compare track section names ignoring capital letters and extra spaces."""
    return section_a.strip().lower() == section_b.strip().lower()


def find_trains_on_section(trains, track_section):
    """Return only the trains that run on the requested track section."""
    return [train for train in trains if same_section(train["track_section"], track_section)]


def intervals_overlap(maintenance_start, maintenance_end, train_start, train_end):
    """
    The project's overlap rule:
        maintenance_start < train_end  AND  train_start < maintenance_end
    A train that ends exactly when maintenance starts (or starts exactly when
    maintenance ends) does NOT overlap.
    """
    return maintenance_start < train_end and train_start < maintenance_end


def find_overlapping_trains(trains_on_section, maintenance_start, maintenance_end):
    """Return the trains (on the section) that overlap the maintenance window."""
    return [
        train for train in trains_on_section
        if intervals_overlap(maintenance_start, maintenance_end, train["start"], train["end"])
    ]


# ---------------------------------------------------------------------------
# 6. Checking the maintenance duration
# ---------------------------------------------------------------------------

def window_duration_minutes(start, end):
    """Length of the proposed window in whole minutes."""
    return int((end - start).total_seconds() // 60)


def check_duration(window_minutes, required_minutes):
    """Return a reason text if the window is too short, otherwise None."""
    if window_minutes < required_minutes:
        return (
            f"Maintenance window is only {window_minutes} minutes long but "
            f"{required_minutes} minutes are required"
        )
    return None


# ---------------------------------------------------------------------------
# 7. Checking resources
# ---------------------------------------------------------------------------

def build_resource_table(rows):
    """
    Turn resource CSV rows into a lookup table.

    Returns (table, invalid_records) where table maps a lower-case resource
    name to the list of availability flags found for it.
    """
    table = {}
    invalid_records = []

    for line_number, row in rows:
        problems = []
        if "__problem__" in row:
            problems.append(row["__problem__"])
        name = row.get("resource_name", "")
        flag = row.get("available", "").lower()
        if not name:
            problems.append("resource_name is empty")
        if flag in TRUE_VALUES:
            is_available = True
        elif flag in FALSE_VALUES:
            is_available = False
        else:
            is_available = None
            problems.append(f"available value '{row.get('available', '')}' is not true/false")

        if problems:
            invalid_records.append({
                "line_number": line_number,
                "resource_name": name,
                "problems": problems,
            })
        elif name:
            # Remember every flag, so duplicate/contradicting rows can be noticed.
            table.setdefault(name.lower(), []).append(is_available)
        # (rows with problems are never added to the table)

    # A name that also appears in an invalid row cannot be trusted either.
    for record in invalid_records:
        if record["resource_name"]:
            table.setdefault(record["resource_name"].lower(), []).append(None)

    return table, invalid_records


def check_resources(requested_names, table):
    """
    Check every requested resource. Returns a list of dictionaries with a
    status of AVAILABLE, UNAVAILABLE, NOT_FOUND or INVALID_DATA.
    """
    results = []
    for name in requested_names:
        flags = table.get(name.lower())
        if flags is None:
            status = "NOT_FOUND"
            message = f"Resource '{name}' does not exist in the resource data"
        elif None in flags or len(set(flags)) > 1:
            status = "INVALID_DATA"
            message = f"Resource '{name}' has invalid or contradicting data, so it cannot be trusted"
        elif flags[0]:
            status = "AVAILABLE"
            message = f"Resource '{name}' is available"
        else:
            status = "UNAVAILABLE"
            message = f"Resource '{name}' is not available"
        results.append({"resource_name": name, "status": status, "message": message})
    return results


# ---------------------------------------------------------------------------
# 8. Producing the structured validation response
# ---------------------------------------------------------------------------

def validate_maintenance(request_data,
                         schedule_path=DEFAULT_SCHEDULE_PATH,
                         resources_path=DEFAULT_RESOURCES_PATH):
    """
    Run every check and return a JSON-friendly dictionary.

    Raises:
        InvalidRequestError - the request itself is malformed.
        DataFileError       - a CSV file is missing/unreadable/lacks columns.

    Any problem with the data makes the result CONFLICT ("fail closed"), so
    bad data can never produce a false VALID.
    """
    request = parse_maintenance_request(request_data)
    section = request["track_section"]
    start, end = request["start"], request["end"]
    window_minutes = window_duration_minutes(start, end)

    schedule_rows = load_csv_file(schedule_path, SCHEDULE_COLUMNS)
    resource_rows = load_csv_file(resources_path, RESOURCE_COLUMNS)

    trains, invalid_schedule = validate_schedule_rows(schedule_rows)
    resource_table, invalid_resources = build_resource_table(resource_rows)

    reasons = []

    # Check A: schedule data quality (fail closed)
    if invalid_schedule:
        reasons.append(
            f"Train schedule data contains {len(invalid_schedule)} invalid record(s), "
            "so the window cannot be confirmed as safe. Fix the data and try again"
        )

    # Check B: is the track section known? (a typo must not give a false VALID)
    trains_on_section = find_trains_on_section(trains, section)
    section_known = any(
        same_section(row.get("track_section", ""), section) for _, row in schedule_rows
    )
    if not section_known:
        reasons.append(
            f"Track section '{section}' does not appear in the train schedule data, "
            "so it cannot be checked"
        )

    # Check C: maintenance duration
    duration_reason = check_duration(window_minutes, request["required_duration_minutes"])
    if duration_reason:
        reasons.append(duration_reason)

    # Check D: overlapping trains on this section only
    overlapping = find_overlapping_trains(trains_on_section, start, end)
    for train in overlapping:
        name = f" ({train['train_name']})" if train["train_name"] else ""
        reasons.append(
            f"Train {train['train_id']}{name} runs {format_datetime(train['start'])} to "
            f"{format_datetime(train['end'])} and overlaps the proposed maintenance window"
        )
    affected_trains = sorted({train["train_id"] for train in overlapping})

    # Check E: resources
    resource_results = check_resources(request["required_resources"], resource_table)
    for result in resource_results:
        if result["status"] != "AVAILABLE":
            reasons.append(result["message"])

    return {
        "status": "CONFLICT" if reasons else "VALID",
        "track_section": section,
        "start_time": format_datetime(start),
        "end_time": format_datetime(end),
        "required_duration_minutes": request["required_duration_minutes"],
        "window_duration_minutes": window_minutes,
        "affected_trains": affected_trains,
        "reasons": reasons,
        "resource_results": resource_results,
        "invalid_schedule_records": invalid_schedule,
        "invalid_resource_records": invalid_resources,
        "note": ACADEMIC_NOTE,
    }


# ---------------------------------------------------------------------------
# Quick demo: run `python main.py`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    example_request = {
        "track_section": "SEC-01",
        "start_time": "2026-10-15 13:00",
        "end_time": "2026-10-15 14:00",
        "required_duration_minutes": 60,
        "required_resources": ["Maintenance Team", "Repair Equipment"],
    }
    try:
        print(json.dumps(validate_maintenance(example_request), indent=2))
    except (InvalidRequestError, DataFileError) as problem:
        print(f"Error: {problem}")
