KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
KAFKA_INPUT_TOPIC = "sensor-events"
KAFKA_OUTPUT_TOPIC = "alerts"
KAFKA_GROUP_ID = "anomaly-detector-group"

WINDOW_SIZE = 20   # number of readings per sliding window per sensor per machine

ASSET_SERVICE_URL = "http://localhost:8002"
NOTIFICATION_SERVICE_URL = "http://localhost:8006"

# Average value thresholds that trigger a status change.
# For NORMAL sensors (temperature, vibration): HIGH average = bad.
# For INVERSE sensors (pressure, rpm):         LOW average = bad.
THRESHOLDS: dict[str, dict[str, float]] = {
    "temperature": {"DEGRADING": 85.0,  "CRITICAL": 100.0},
    "vibration":   {"DEGRADING": 2.5,   "CRITICAL": 5.0},
    "pressure":    {"DEGRADING": 5.0,   "CRITICAL": 3.0},   # below these = bad
    "rpm":         {"DEGRADING": 1200,  "CRITICAL": 900},   # below these = bad
}

# Sensors where a LOW average is the anomaly (opposite direction check)
INVERSE_SENSORS = {"pressure", "rpm"}
