
import pandas as pd
import os
from datetime import datetime
import uuid

# Existing data folder
BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_FOLDER, "data")

os.makedirs(DATA_FOLDER, exist_ok=True)

CSV_FILE = os.path.join(
    DATA_FOLDER, "maintenance_requests.csv"
)

COLUMNS = [
    "request_id",
    "track_section",
    "requested_date",
    "start_time",
    "end_time",
    "duration_minutes",
    "priority",
    "required_resources",
    "status"
]


def get_input(message):
    return input(message).strip()


def submit_request():
    print("\n===== KAVACH BIE Maintenance Request Form =====")

    # Track section
    track_section = get_input(
        "Enter track section (example: TPTY-RU): "
    ).upper()

    if not track_section or "-" not in track_section:
        print("Invalid track section. Example: TPTY-RU")
        return

    # Date validation
    requested_date = get_input(
        "Enter maintenance date (YYYY-MM-DD): "
    )

    try:
        datetime.strptime(requested_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format!")
        return

    # Time validation
    start_time = get_input("Enter start time (HH:MM): ")
    end_time = get_input("Enter end time (HH:MM): ")

    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
    except ValueError:
        print("Invalid time! Use HH:MM format.")
        return

    if end <= start:
        print("End time must be after start time on the same day.")
        return

    duration = int((end - start).total_seconds() / 60)

    # Priority validation
    priority = get_input(
        "Enter priority (Low/Medium/High/Critical): "
    ).capitalize()

    valid_priorities = [
        "Low", "Medium", "High", "Critical"
    ]

    if priority not in valid_priorities:
        print("Invalid priority!")
        return

    # Resources validation
    resources = get_input(
        "Enter required resources (comma-separated): "
    )

    if not resources:
        print("Required resources cannot be empty!")
        return

    # Create request
    request = {
        "request_id": str(uuid.uuid4())[:8],
        "track_section": track_section,
        "requested_date": requested_date,
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration,
        "priority": priority,
        "required_resources": resources,
        "status": "Pending"
    }

    # Append request to existing CSV
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        existing = pd.read_csv(CSV_FILE)
        existing = existing.reindex(columns=COLUMNS)
        existing.loc[len(existing)] = request
        existing.to_csv(CSV_FILE, index=False)
    else:
        pd.DataFrame([request], columns=COLUMNS).to_csv(
            CSV_FILE, index=False
        )

    print("\nMaintenance request saved successfully!")
    print("Request ID:", request["request_id"])
    print("Duration:", duration, "minutes")
    print("Status: Pending")
    print("Saved file:", CSV_FILE)


if __name__ == "__main__":
    submit_request()
