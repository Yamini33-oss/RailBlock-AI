
import os
import pandas as pd

# Project data folder
BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_FOLDER, "data")


def validate_file(filename, required_columns):
    path = os.path.join(DATA_FOLDER, filename)

    print("\n" + "=" * 50)
    print("Checking:", filename)
    print("=" * 50)

    # Check whether file exists
    if not os.path.exists(path):
        print("ERROR: File not found!")
        return

    # Read CSV safely
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        print("ERROR: CSV file is empty.")
        return
    except Exception as error:
        print("ERROR while reading file:", error)
        return

    print("Total rows:", len(df))
    print("Columns:", df.columns.tolist())

    # Check required columns
    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        print("ERROR: Missing columns:", missing_columns)
        return

    print("Required columns: OK")

    # Check missing values
    missing_values = df[required_columns].isnull().sum()
    missing_values = missing_values[missing_values > 0]

    if len(missing_values) > 0:
        print("WARNING: Missing values found:")
        print(missing_values)
    else:
        print("Missing values: None")

    return df


def check_schedule():
    df = validate_file(
        "train_schedule.csv",
        [
            "train_id",
            "train_name",
            "track_section",
            "departure_time",
            "arrival_time",
            "scheduled_running_minutes"
        ]
    )

    if df is None:
        return

    # Check empty train IDs and track sections
    for col in ["train_id", "track_section"]:
        if df[col].astype("string").str.strip().eq("").any():
            print("WARNING: Empty values in", col)

    # Check running duration
    duration = pd.to_numeric(
        df["scheduled_running_minutes"],
        errors="coerce"
    )

    if duration.isna().any():
        print("WARNING: Invalid running duration found.")
    elif (duration < 0).any():
        print("ERROR: Negative running duration found.")
    else:
        print("Running duration: OK")

    # Check time format
    for col in ["departure_time", "arrival_time"]:
        valid = df[col].astype("string").str.match(
            r"^\d{1,2}:\d{2}(:\d{2})?$",
            na=False
        )
        if not valid.all():
            print("WARNING: Invalid times in", col)
        else:
            print(col, ": OK")


def check_delays():
    df = validate_file(
        "historical_delays.csv",
        [
            "train_name",
            "route",
            "date",
            "scheduled_arrival",
            "actual_arrival",
            "delay_minutes"
        ]
    )

    if df is None:
        return

    # Check date format
    dates = pd.to_datetime(df["date"], errors="coerce")

    if dates.isna().any():
        print("WARNING: Invalid dates found.")
    else:
        print("Dates: OK")

    # Check delay values
    delay = pd.to_numeric(
        df["delay_minutes"],
        errors="coerce"
    )

    if delay.isna().any():
        print("WARNING: Invalid delay values found.")
    else:
        print("Delay values: OK")

    # Negative delay can mean the train arrived early.


def check_traffic():
    df = validate_file(
        "traffic_density.csv",
        [
            "track_section",
            "time_period",
            "train_count",
            "traffic_level"
        ]
    )

    if df is None:
        return

    count = pd.to_numeric(
        df["train_count"],
        errors="coerce"
    )

    if count.isna().any():
        print("WARNING: Invalid train counts found.")
    elif (count < 0).any():
        print("ERROR: Negative train count found.")
    else:
        print("Train counts: OK")

    valid_levels = ["Low", "Medium", "High"]

    if df["traffic_level"].isin(valid_levels).all():
        print("Traffic levels: OK")
    else:
        print("WARNING: Unknown traffic level found.")


def check_maintenance():
    df = validate_file(
        "maintenance_requests.csv",
        [
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
    )

    if df is None:
        return

    # Check date format
    dates = pd.to_datetime(
        df["requested_date"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    if dates.isna().any():
        print("WARNING: Invalid maintenance dates.")
    else:
        print("Maintenance dates: OK")

    # Check start and end times
    for col in ["start_time", "end_time"]:
        valid = df[col].astype("string").str.match(
            r"^\d{2}:\d{2}$",
            na=False
        )

        if not valid.all():
            print("WARNING: Invalid times in", col)
        else:
            print(col, ": OK")

    # Check duration
    duration = pd.to_numeric(
        df["duration_minutes"],
        errors="coerce"
    )

    if duration.isna().any() or (duration <= 0).any():
        print("WARNING: Invalid maintenance duration.")
    else:
        print("Maintenance duration: OK")

    valid_priorities = ["Low", "Medium", "High", "Critical"]

    if df["priority"].isin(valid_priorities).all():
        print("Priorities: OK")
    else:
        print("WARNING: Invalid priority found.")


if __name__ == "__main__":
    print("KAVACH BIE - DATA VALIDATION STARTED")

    check_schedule()
    check_delays()
    check_traffic()
    check_maintenance()

    print("\nDATA VALIDATION COMPLETED")
