
import json
import pandas as pd
import os

# Dataset folder
DATA_FOLDER = os.path.join("member1_data", "data")

# JSON file path
json_file = os.path.join(DATA_FOLDER, "trains.json")

# Check file exists
if not os.path.exists(json_file):
    print("ERROR: trains.json file not found!")
    print("Check whether the file is inside member1_data/data/")
    exit()

# Read GitHub dataset
with open(json_file, "r", encoding="utf-8") as file:
    trains = json.load(file)

print("Total trains loaded:", len(trains))

rows = []

# Extract train and route details
for train in trains:
    route = train.get("completeOrderedRoute", [])

    for i in range(len(route) - 1):
        current = route[i]
        next_stop = route[i + 1]

        departure = current.get("departureTime")
        arrival = next_stop.get("arrivalTime")

        if not departure or not arrival:
            continue

        start_day = current.get("journeyDay") or 1
        end_day = next_stop.get("journeyDay") or start_day

        start = pd.to_timedelta(
            int(start_day) - 1, unit="D"
        ) + pd.to_timedelta(departure)

        end = pd.to_timedelta(
            int(end_day) - 1, unit="D"
        ) + pd.to_timedelta(arrival)

        running_minutes = int(
            (end - start).total_seconds() / 60
        )

        # Skip invalid or negative journey durations
        if running_minutes < 0:
            continue

        source = train.get("source", {})
        destination = train.get("destination", {})

        rows.append({
            "train_id": str(train.get("trainNumber", "")),
            "train_name": train.get("trainName", ""),
            "source": source.get("name", ""),
            "destination": destination.get("name", ""),
            "from_station": current.get("stationCode", ""),
            "to_station": next_stop.get("stationCode", ""),
            "track_section": (
                str(current.get("stationCode", ""))
                + "-"
                + str(next_stop.get("stationCode", ""))
            ),
            "departure_time": departure,
            "arrival_time": arrival,
            "scheduled_running_minutes": running_minutes,
            "journey_day": start_day
        })

# Convert extracted data to a table
df = pd.DataFrame(rows)

# Save CSV
output_file = os.path.join(
    DATA_FOLDER, "train_schedule.csv"
)
df.to_csv(output_file, index=False)

print("CSV created successfully!")
print("Total route segments:", len(df))
print("Saved at:", output_file)
print(df.head(5))
