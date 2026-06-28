"""
Orchestration Runner — Phase 7, AMLO

Consumes the Kafka 'alerts' topic and triggers the full agent graph
for every CRITICAL alert. Runs as its own process alongside the other services.

Run: python runner.py
"""

import json
from kafka import KafkaConsumer

from graph import run_orchestration

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
ALERTS_TOPIC = "alerts"


def main():
    consumer = KafkaConsumer(
        ALERTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="orchestration-group",
        auto_offset_reset="latest",
        api_version=(3, 7, 0),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    print("Orchestration Runner started")
    print(f"  Topic   : {ALERTS_TOPIC}")
    print(f"  Triggers: CRITICAL severity only\n")

    for message in consumer:
        event = message.value
        severity  = event.get("severity", "")
        machine_id = event.get("machine_id", "")

        if severity != "CRITICAL":
            print(f"[SKIP] {machine_id} | {severity}")
            continue

        print(f"\n{'='*60}")
        print(f"[TRIGGER] {machine_id} | {event.get('sensor_type')} | CRITICAL")
        print(f"{'='*60}")

        try:
            result = run_orchestration(event)
            print("\n[DONE] Pipeline complete:")
            print(f"  Work Order  : #{result.get('work_order_id')}")
            print(f"  AGV         : {result.get('agv_id')} dispatched ({len(result.get('agv_route') or [])} steps)")
            t = result.get("technician")
            print(f"  Technician  : {t.get('name') if t else 'None'}")
            po = result.get("purchase_orders_created") or []
            print(f"  POs created : {len(po)} ({', '.join(po) if po else 'none'})")
        except Exception as e:
            print(f"[ERROR] Orchestration failed: {e}")


if __name__ == "__main__":
    main()
