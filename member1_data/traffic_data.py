
import pandas as pd
import os

# Locate existing data folder
folder = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data"
)

schedule_file = os.path.join(
    folder, "train_schedule.csv"
)

output_file = os.path.join(
    folder, "traffic_density.csv"
)

if not os.path.exists(schedule_file):
    print("train_schedule.csv not found!")
    exit()

df = pd.read_csv(schedule_file)

required = [
    "train_id",
    "track_section",
    "departure_time"
]

for column in required:
    if column not in df.columns:
        print("Missing column:", column)
        exit()

# Extract hour from departure time
df["hour"] = pd.to_datetime(
    df["departure_time"],
    format="mixed",
    errors="coerce"
).dt.hour

df = df.dropna(
    subset=["track_section", "hour"]
)

# Count train departures for each section and hour
traffic = df.groupby(
    ["track_section", "hour"]
).agg(
    train_count=("train_id", "nunique")
).reset_index()

# Assign estimated traffic level
def get_traffic_level(count):
    if count <= 3:
        return "Low"
    elif count <= 7:
        return "Medium"
    else:
        return "High"

traffic["traffic_level"] = traffic[
    "train_count"
].apply(get_traffic_level)

traffic["time_period"] = traffic["hour"].apply(
    lambda h: f"{int(h):02d}:00-{(int(h) + 1) % 24:02d}:00"
)

traffic = traffic[
    [
        "track_section",
        "time_period",
        "train_count",
        "traffic_level"
    ]
]

traffic.to_csv(output_file, index=False)

print("Traffic density dataset created!")
print("Total records:", len(traffic))
print("Saved to:", output_file)
print(traffic.head(10))
