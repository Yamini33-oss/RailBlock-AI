
import pandas as pd
import os

folder = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data"
)

input_file = os.path.join(
    folder, "indian_railway_delays_dataset.csv"
)

output_file = os.path.join(
    folder, "historical_delays.csv"
)

if not os.path.exists(input_file):
    print("Dataset file not found:", input_file)
    exit()

# Read downloaded GitHub dataset
df = pd.read_csv(input_file)

print("Original columns:", df.columns.tolist())

# Convert GitHub column names to project column names
df = df.rename(columns={
    "Train_Name": "train_name",
    "Route": "route",
    "Scheduled_Arrival": "scheduled_arrival",
    "Actual_Arrival": "actual_arrival",
    "Delay_Minutes": "delay_minutes",
    "Date": "date"
})

# Keep the available historical delay fields
required = [
    "train_name",
    "route",
    "date",
    "scheduled_arrival",
    "actual_arrival",
    "delay_minutes"
]

missing = [col for col in required if col not in df.columns]

if missing:
    print("Required columns not found:", missing)
    print("Check the downloaded dataset column names.")
    exit()

df = df[required]

# Remove rows without essential delay information
df = df.dropna(
    subset=["train_name", "date", "delay_minutes"]
)

df.to_csv(output_file, index=False)

print("\nHistorical delay CSV created!")
print("Rows:", len(df))
print("Saved to:", output_file)
print(df.head())
