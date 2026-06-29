"""
Sensor Service — Phase 3, AMLO

Consumes sensor-events from Kafka and persists each reading to MongoDB.
Thin by design — no processing, no anomaly detection. Raw persistence only.

Run: python service.py
"""

import json
from datetime import datetime

from kafka import KafkaConsumer
from pymongo import MongoClient

from config import (
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_GROUP_ID,
    MONGO_URI, MONGO_DB, MONGO_COLLECTION
)


def build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )


def main():
    collection = MongoClient(MONGO_URI)[MONGO_DB][MONGO_COLLECTION]

    print(f"Sensor Service started")
    print(f"  Consuming : {KAFKA_TOPIC} (group: {KAFKA_GROUP_ID})")
    print(f"  Writing to: MongoDB → {MONGO_DB}.{MONGO_COLLECTION}\n")

    while True:
        try:
            consumer = build_consumer()
            for message in consumer:
                doc = message.value
                doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])
                collection.insert_one(doc)
                print(
                    f"[offset {message.offset:>6}] "
                    f"{doc['machine_id']:<10} | "
                    f"{doc['sensor_type']:<12} {doc['value']:>7} {doc['unit']:<8} | "
                    f"{doc['machine_status']}"
                )
        except ValueError as e:
            if "Invalid file descriptor" in str(e):
                print("[WARN] Kafka selector error — restarting consumer...")
                try:
                    consumer.close()
                except Exception:
                    pass
                continue
            raise


if __name__ == "__main__":
    main()
