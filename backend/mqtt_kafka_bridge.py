"""
MQTT → Kafka Bridge — AMLO

Subscribes to MQTT sensor readings from the IoT emulator and:
  1. Publishes every reading to Kafka 'sensor-events' topic
  2. On CRITICAL/DEGRADING machine_status: publishes to Kafka 'alerts' topic
     and POSTs to the notification service for live WebSocket broadcast

Run: python mqtt_kafka_bridge.py
"""

import json
import time
import httpx
import paho.mqtt.client as mqtt
from kafka import KafkaProducer
from datetime import datetime, timezone

MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
MQTT_TOPIC    = "amlo/sensors/#"

KAFKA_SERVERS     = "localhost:9092"
SENSOR_TOPIC      = "sensor-events"
ALERTS_TOPIC      = "alerts"

ASSET_URL         = "http://127.0.0.1:8002"
NOTIFY_URL        = "http://127.0.0.1:8006"

# machine_id → machine_type lookup (populated at startup)
_machine_types: dict[str, str] = {}


def _load_machine_types():
    for attempt in range(10):
        try:
            r = httpx.get(f"{ASSET_URL}/machines", timeout=5.0)
            if r.status_code == 200:
                for m in r.json():
                    _machine_types[m["machine_id"]] = m.get("type", "Unknown")
                print(f"[Bridge] Loaded {len(_machine_types)} machine types")
                return
        except Exception:
            pass
        print(f"[Bridge] Asset service not ready, retrying ({attempt+1}/10)...")
        time.sleep(3)
    print("[Bridge] Could not load machine types — alerts will use 'Unknown' type")


def _make_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        api_version=(3, 7, 0),
    )


def _on_message(client, userdata, msg):
    producer: KafkaProducer = userdata["producer"]
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        return

    # Always publish to sensor-events
    producer.send(SENSOR_TOPIC, payload)

    status = payload.get("machine_status", "NORMAL")
    if status in ("CRITICAL", "DEGRADING"):
        machine_id   = payload.get("machine_id", "")
        machine_type = _machine_types.get(machine_id, "Unknown")
        sensor_type  = payload.get("sensor_type", "")
        value        = payload.get("value", 0.0)

        alert = {
            "machine_id":    machine_id,
            "machine_type":  machine_type,
            "sensor_type":   sensor_type,
            "severity":      status,
            "average_value": value,
            "timestamp":     payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
        producer.send(ALERTS_TOPIC, alert)

        # Notify WebSocket clients
        try:
            httpx.post(f"{NOTIFY_URL}/notify", json={
                "event_type":  "ANOMALY_DETECTED",
                "actor":       "mqtt_kafka_bridge",
                "entity_type": "machine",
                "entity_id":   machine_id,
                "payload":     alert,
            }, timeout=2.0)
        except Exception:
            pass

        print(f"[Bridge] {status} alert → {machine_id} | {sensor_type} = {value}")


def main():
    _load_machine_types()

    producer = _make_producer()

    client = mqtt.Client(userdata={"producer": producer})
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_TOPIC)
    client.on_message = _on_message

    print(f"[Bridge] Listening on MQTT {MQTT_TOPIC} → Kafka ({SENSOR_TOPIC}, {ALERTS_TOPIC})")
    client.loop_forever()


if __name__ == "__main__":
    main()
