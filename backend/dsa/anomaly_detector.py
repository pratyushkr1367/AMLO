"""
Sliding Window Anomaly Detector — Phase 5, AMLO

Consumes sensor-events from Kafka. Maintains a CircularQueue(WINDOW_SIZE) per
machine × sensor. On each reading, computes the window average and checks it
against thresholds. When a threshold is crossed, it:
  1. Publishes an alert to the Kafka 'alerts' topic
  2. Updates the machine status in PostgreSQL via the Asset Service
  3. Logs the event via the Notification Service

Only fires when severity CHANGES — no duplicate alerts for sustained anomalies.

Run: python anomaly_detector.py
"""

import json
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from kafka import KafkaConsumer, KafkaProducer

from circular_queue import CircularQueue
from config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_INPUT_TOPIC, KAFKA_OUTPUT_TOPIC,
    KAFKA_GROUP_ID, WINDOW_SIZE, THRESHOLDS, INVERSE_SENSORS,
    ASSET_SERVICE_URL, NOTIFICATION_SERVICE_URL,
)


def _build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        KAFKA_INPUT_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="latest",
        api_version=(3, 7, 0),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )


def _build_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
    )


def _evaluate_severity(sensor_type: str, average: float) -> str:
    """Return 'NORMAL', 'DEGRADING', or 'CRITICAL' based on the window average."""
    thresholds = THRESHOLDS.get(sensor_type)
    if not thresholds:
        return "NORMAL"

    if sensor_type in INVERSE_SENSORS:
        if average <= thresholds["CRITICAL"]:
            return "CRITICAL"
        elif average <= thresholds["DEGRADING"]:
            return "DEGRADING"
    else:
        if average >= thresholds["CRITICAL"]:
            return "CRITICAL"
        elif average >= thresholds["DEGRADING"]:
            return "DEGRADING"

    return "NORMAL"


def _update_machine_status(machine_id: str, status: str):
    try:
        httpx.patch(
            f"{ASSET_SERVICE_URL}/machines/{machine_id}/status",
            json={"status": status},
            timeout=3.0,
        )
    except Exception as e:
        print(f"  [WARN] Could not update Asset Service: {e}")


def _notify(machine_id: str, sensor_type: str, severity: str, average: float):
    payload = {
        "event_type": "ANOMALY_DETECTED",
        "actor": "anomaly_detector",
        "entity_type": "machine",
        "entity_id": machine_id,
        "payload": {
            "sensor_type": sensor_type,
            "average_value": round(average, 2),
            "severity": severity,
            "window_size": WINDOW_SIZE,
        },
    }
    try:
        httpx.post(f"{NOTIFICATION_SERVICE_URL}/notify", json=payload, timeout=3.0)
    except Exception as e:
        print(f"  [WARN] Could not reach Notification Service: {e}")


def main():
    producer = _build_producer()

    queues: dict[str, dict[str, CircularQueue]] = defaultdict(
        lambda: defaultdict(lambda: CircularQueue(WINDOW_SIZE))
    )
    last_severity: dict[str, dict[str, str]] = defaultdict(lambda: defaultdict(lambda: "NORMAL"))

    print(f"Anomaly Detector started")
    print(f"  Consuming : {KAFKA_INPUT_TOPIC} (group: {KAFKA_GROUP_ID})")
    print(f"  Window    : {WINDOW_SIZE} readings per sensor per machine")
    print(f"  Publishing: {KAFKA_OUTPUT_TOPIC}\n")

    while True:
        try:
            consumer = _build_consumer()
            _run(consumer, producer, queues, last_severity)
        except ValueError as e:
            if "Invalid file descriptor" in str(e):
                print("[WARN] Kafka selector error — restarting consumer...")
                try:
                    consumer.close()
                except Exception:
                    pass
                continue
            raise


def _run(consumer, producer, queues, last_severity):
    for message in consumer:
        reading = message.value
        machine_id  = reading["machine_id"]
        sensor_type = reading["sensor_type"]
        value       = reading["value"]

        queue = queues[machine_id][sensor_type]
        queue.push(value)

        # Only evaluate once the window has enough data
        if not queue.is_full():
            continue

        average  = queue.average()
        severity = _evaluate_severity(sensor_type, average)
        previous = last_severity[machine_id][sensor_type]

        if severity == previous:
            continue  # no change — skip

        last_severity[machine_id][sensor_type] = severity

        if severity != "NORMAL":
            alert = {
                "event_type":   "ANOMALY_DETECTED",
                "machine_id":   machine_id,
                "sensor_type":  sensor_type,
                "average_value": round(average, 2),
                "severity":     severity,
                "detected_at":  datetime.now(timezone.utc).isoformat(),
                "machine_type": reading.get("machine_type", ""),
            }
            producer.send(KAFKA_OUTPUT_TOPIC, value=alert)
            producer.flush()

            _update_machine_status(machine_id, severity)
            _notify(machine_id, sensor_type, severity, average)

            print(
                f"[ALERT] {machine_id} | {sensor_type} avg={round(average,2)} "
                f"→ {severity}  (was {previous})"
            )
        else:
            # Recovered to NORMAL — update status and log
            _update_machine_status(machine_id, "NORMAL")
            print(f"[RECOVER] {machine_id} | {sensor_type} avg={round(average,2)} → NORMAL")


if __name__ == "__main__":
    main()
