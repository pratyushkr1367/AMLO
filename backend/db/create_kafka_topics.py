"""
Creates the three Kafka topics AMLO needs.
Run once after the Docker stack is up.

Run: python backend/db/create_kafka_topics.py
"""

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

BOOTSTRAP_SERVERS = "localhost:9092"

TOPICS = [
    # 3 partitions: 7 machines can be spread across partitions,
    # and the consumer group can scale to 3 instances later.
    NewTopic(name="sensor-events", num_partitions=3, replication_factor=1),
    NewTopic(name="alerts",        num_partitions=1, replication_factor=1),
    NewTopic(name="agv-updates",   num_partitions=1, replication_factor=1),
]

admin = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS)

for topic in TOPICS:
    try:
        admin.create_topics([topic])
        print(f"  Created  : {topic.name}")
    except TopicAlreadyExistsError:
        print(f"  Exists   : {topic.name} (skipped)")

admin.close()
print("\nDone.")
