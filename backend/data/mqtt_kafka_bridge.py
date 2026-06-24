"""
MQTT → Kafka Bridge — AMLO Data Ingestion

Subscribes to all AMLO MQTT topics and forwards messages to the appropriate Kafka topics.

MQTT topic mapping:
  amlo/sensors/# → Kafka: sensor-events
  amlo/agv/#     → Kafka: agv-updates

Run: python backend/data/mqtt_kafka_bridge.py
"""

import json
import paho.mqtt.client as mqtt
from kafka import KafkaProducer

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    acks="all",
    retries=3,
)


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker (rc={rc})")
    client.subscribe("amlo/#")
    print("Subscribed to amlo/#\n")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print(f"[WARN] Failed to parse message on {msg.topic}: {e}")
        return

    if msg.topic.startswith("amlo/sensors/"):
        kafka_topic = "sensor-events"
        label = payload.get("machine_id", "?")
    elif msg.topic.startswith("amlo/agv/"):
        kafka_topic = "agv-updates"
        label = payload.get("agv_id", "?")
    else:
        print(f"[WARN] No Kafka mapping for MQTT topic: {msg.topic}")
        return

    producer.send(kafka_topic, value=payload)
    print(f"[{msg.topic}]  →  Kafka:{kafka_topic}  |  {label}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print("MQTT → Kafka Bridge starting...")
    print(f"  MQTT  : {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Kafka : {KAFKA_BOOTSTRAP_SERVERS}")

    client.connect(MQTT_BROKER, MQTT_PORT)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nShutting down bridge...")
        producer.close()
        client.disconnect()


if __name__ == "__main__":
    main()
