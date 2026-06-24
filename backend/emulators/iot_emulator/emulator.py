"""
IoT Sensor Emulator — Phase 2, AMLO

Simulates N factory machines cycling through NORMAL → DEGRADING → CRITICAL states.
Publishes one MQTT message per sensor per machine on every tick.

MQTT topic: amlo/sensors/{machine_id}/{sensor_type}

Run: python emulator.py
"""

import json
import random
import time
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_PREFIX,
    TICK_INTERVAL, ANOMALY_INTERVAL, MACHINES
)
from machine import Machine


def build_mqtt_client() -> mqtt.Client:
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()
    return client


def publish_readings(client: mqtt.Client, machine: Machine):
    for reading in machine.generate_readings():
        payload = {
            "machine_id":     machine.machine_id,
            "machine_status": machine.status,
            "sensor_type":    reading["sensor_type"],
            "value":          reading["value"],
            "unit":           reading["unit"],
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        }
        topic = f"{MQTT_TOPIC_PREFIX}/{machine.machine_id}/{reading['sensor_type']}"
        client.publish(topic, json.dumps(payload))


def anomaly_injector(machines: list[Machine], stop_event: threading.Event):
    """Background thread: every ANOMALY_INTERVAL seconds, push a random machine to CRITICAL."""
    while not stop_event.wait(ANOMALY_INTERVAL):
        target = random.choice(machines)
        previous = target.status
        target.set_status("CRITICAL")
        print(f"  [ANOMALY] {target.machine_id} forced to CRITICAL (was {previous})")


def main():
    machines = [Machine(**m) for m in MACHINES]
    client = build_mqtt_client()

    stop_event = threading.Event()
    injector_thread = threading.Thread(
        target=anomaly_injector,
        args=(machines, stop_event),
        daemon=True
    )
    injector_thread.start()

    print(f"IoT Emulator started — {len(machines)} machines")
    print(f"  Publishing to MQTT: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Topic prefix      : {MQTT_TOPIC_PREFIX}/{{machine_id}}/{{sensor_type}}")
    print(f"  Tick interval     : {TICK_INTERVAL}s | Anomaly interval: {ANOMALY_INTERVAL}s\n")

    try:
        while True:
            for machine in machines:
                drifted_to = machine.apply_drift()
                if drifted_to:
                    print(f"  [DRIFT] {machine.machine_id} → {drifted_to}")
                publish_readings(client, machine)

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Tick — {len(machines) * 4} messages published  |  "
                + "  ".join(f"{m.machine_id}:{m.status}" for m in machines)
            )
            time.sleep(TICK_INTERVAL)

    except KeyboardInterrupt:
        print("\nShutting down emulator...")
        stop_event.set()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
