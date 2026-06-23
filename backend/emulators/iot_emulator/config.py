KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "sensor-events"

TICK_INTERVAL = 2       # seconds between each sensor reading batch
ANOMALY_INTERVAL = 60   # seconds between random anomaly injections

# Must match the seed data in 001_initial_schema.sql
MACHINES = [
    {"machine_id": "CNC-01",   "name": "CNC Machine 1",     "type": "CNC",    "location_row": 5,  "location_col": 10},
    {"machine_id": "CNC-02",   "name": "CNC Machine 2",     "type": "CNC",    "location_row": 5,  "location_col": 20},
    {"machine_id": "LATHE-01", "name": "Lathe Machine 1",   "type": "Lathe",  "location_row": 15, "location_col": 10},
    {"machine_id": "LATHE-02", "name": "Lathe Machine 2",   "type": "Lathe",  "location_row": 15, "location_col": 25},
    {"machine_id": "PRESS-01", "name": "Hydraulic Press 1", "type": "Press",  "location_row": 25, "location_col": 15},
    {"machine_id": "WELD-01",  "name": "Welding Station 1", "type": "Welder", "location_row": 35, "location_col": 10},
    {"machine_id": "WELD-02",  "name": "Welding Station 2", "type": "Welder", "location_row": 35, "location_col": 30},
]

# Sensor value ranges (min, max) per machine status.
# Each sensor drifts within its band — readings outside the NORMAL band
# are what the anomaly detector will flag in Phase 5.
SENSOR_RANGES = {
    "temperature": {          # celsius
        "NORMAL":   (60.0,  80.0),
        "DEGRADING":(80.0, 100.0),
        "CRITICAL": (100.0, 120.0),
    },
    "vibration": {            # mm/s
        "NORMAL":   (0.5,  2.0),
        "DEGRADING":(2.0,  5.0),
        "CRITICAL": (5.0, 10.0),
    },
    "pressure": {             # bar
        "NORMAL":   (6.0,  8.0),
        "DEGRADING":(4.0,  6.0),
        "CRITICAL": (2.0,  4.0),
    },
    "rpm": {                  # revolutions per minute
        "NORMAL":   (1400, 1600),
        "DEGRADING":(1100, 1400),
        "CRITICAL": (700,  1100),
    },
}

SENSOR_UNITS = {
    "temperature": "celsius",
    "vibration":   "mm/s",
    "pressure":    "bar",
    "rpm":         "rpm",
}

# Per-tick probability of spontaneous state drift.
# Keeps the simulation alive even without injected anomalies.
DRIFT_PROBABILITIES = {
    "NORMAL":    {"DEGRADING": 0.005},          # 0.5% chance per tick
    "DEGRADING": {"CRITICAL": 0.01, "NORMAL": 0.008},
    "CRITICAL":  {"DEGRADING": 0.02},           # machines can partially recover
}
