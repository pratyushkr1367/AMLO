import random
from config import SENSOR_RANGES, SENSOR_UNITS, DRIFT_PROBABILITIES


class Machine:
    def __init__(self, machine_id: str, name: str, type: str,
                 location_row: int, location_col: int):
        self.machine_id = machine_id
        self.name = name
        self.type = type
        self.location_row = location_row
        self.location_col = location_col
        self.status = "NORMAL"

    def generate_readings(self) -> list[dict]:
        readings = []
        for sensor_type, ranges in SENSOR_RANGES.items():
            low, high = ranges[self.status]
            value = round(random.uniform(low, high), 2)
            readings.append({
                "sensor_type": sensor_type,
                "value": value,
                "unit": SENSOR_UNITS[sensor_type],
            })
        return readings

    def apply_drift(self):
        """Small per-tick probability of spontaneous state transition."""
        transitions = DRIFT_PROBABILITIES.get(self.status, {})
        roll = random.random()
        cumulative = 0.0
        for next_status, probability in transitions.items():
            cumulative += probability
            if roll < cumulative:
                self.status = next_status
                return next_status
        return None

    def set_status(self, status: str):
        self.status = status
