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
    consumer = build_consumer()
    collection = MongoClient(MONGO_URI)[MONGO_DB][MONGO_COLLECTION]

    print(f"Sensor Service started")
    print(f"  Consuming : {KAFKA_TOPIC} (group: {KAFKA_GROUP_ID})")
    print(f"  Writing to: MongoDB → {MONGO_DB}.{MONGO_COLLECTION}\n")

    for message in consumer:
        doc = message.value

        # Store timestamp as a native datetime so MongoDB can index and
        # query it by time range — the emulator sends it as an ISO string.
        doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])

        collection.insert_one(doc)

        print(
            f"[offset {message.offset:>6}] "
            f"{doc['machine_id']:<10} | "
            f"{doc['sensor_type']:<12} {doc['value']:>7} {doc['unit']:<8} | "
            f"{doc['machine_status']}"
        )


if __name__ == "__main__":
    main()
