GRID_SIZE = 50
STEP_INTERVAL = 0.5    # seconds between each grid cell move

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "amlo/agv"  # publishes to amlo/agv/{agv_id}/position

# Starting positions for each AGV on the 50x50 grid
AGVS = [
    {"agv_id": "AGV-01", "start_row": 0,  "start_col": 0},
    {"agv_id": "AGV-02", "start_row": 0,  "start_col": 49},
    {"agv_id": "AGV-03", "start_row": 49, "start_col": 0},
]
