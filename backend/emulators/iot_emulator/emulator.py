"""
IoT Sensor Emulator — Phase 2, AMLO

Simulates N factory machines cycling through NORMAL → DEGRADING → CRITICAL states.
Publishes one Kafka message per sensor per machine on every tick.

Run: python emulator.py
"""

import json
import random
import time
import threading
from datetime import datetime, timezone

from kafka import KafkaProducer

from config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC,
    TICK_INTERVAL, ANOMALY_INTERVAL, MACHINES
)
from machine import Machine


def build_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",         # wait for broker confirmation before returning
        retries=3,
    )


def publish_readings(producer: KafkaProducer, machine: Machine):
    for reading in machine.generate_readings():
        payload = {
            "machine_id":     machine.machine_id,
            "machine_status": machine.status,
            "sensor_type":    reading["sensor_type"],
            "value":          reading["value"],
            "unit":           reading["unit"],
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        }
        producer.send(KAFKA_TOPIC, value=payload)


def anomaly_injector(machines: list[Machine], stop_event: threading.Event):
    """Background thread: every ANOMALY_INTERVAL seconds, push a random machine to CRITICAL."""
    while not stop_event.wait(ANOMALY_INTERVAL):
        target = random.choice(machines)
        previous = target.status
        target.set_status("CRITICAL")
        print(f"  [ANOMALY] {target.machine_id} forced to CRITICAL (was {previous})")


def main():
    machines = [Machine(**m) for m in MACHINES]
    producer = build_producer()

    stop_event = threading.Event()
    injector_thread = threading.Thread(
        target=anomaly_injector,
        args=(machines, stop_event),
        daemon=True
    )
    injector_thread.start()

    print(f"Emulator started — {len(machines)} machines, "
          f"tick every {TICK_INTERVAL}s, anomaly every {ANOMALY_INTERVAL}s")
    print(f"Publishing to Kafka topic '{KAFKA_TOPIC}' at {KAFKA_BOOTSTRAP_SERVERS}\n")

    try:
        while True:
            for machine in machines:
                drifted_to = machine.apply_drift()
                if drifted_to:
                    print(f"  [DRIFT] {machine.machine_id} → {drifted_to}")

                publish_readings(producer, machine)

            producer.flush()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Tick published — {len(machines) * 4} messages  |  "
                  + "  ".join(f"{m.machine_id}:{m.status}" for m in machines))

            time.sleep(TICK_INTERVAL)

    except KeyboardInterrupt:
        print("\nShutting down emulator...")
        stop_event.set()
        producer.close()


if __name__ == "__main__":
    main()
