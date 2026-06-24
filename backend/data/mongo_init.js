// Run with:
// Get-Content backend/db/mongo_init.js | docker exec -i amlo_mongodb mongosh -u amlo -p amlo_secret --authenticationDatabase admin amlo_db

db = db.getSiblingDB("amlo_db");

// ─── telemetry ────────────────────────────────────────────────────────────────
// One document per sensor reading published by the IoT emulator via Kafka.
// High write volume — the Sensor Service inserts here on every Kafka message.
db.createCollection("telemetry", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["machine_id", "timestamp", "sensor_type", "value", "unit", "machine_status"],
      properties: {
        machine_id:     { bsonType: "string",
                          description: "e.g. CNC-01" },
        timestamp:      { bsonType: "date" },
        sensor_type:    { bsonType: "string",
                          enum: ["temperature", "vibration", "pressure", "rpm"] },
        value:          { bsonType: "number" },
        unit:           { bsonType: "string",
                          description: "e.g. celsius, mm/s, bar, rpm" },
        machine_status: { bsonType: "string",
                          enum: ["NORMAL", "DEGRADING", "CRITICAL", "OFFLINE"] }
      }
    }
  }
});

// Compound index: the Sensor Service and Anomaly Detector always query
// by machine_id first, then slice by time window.
db.telemetry.createIndex({ machine_id: 1, timestamp: -1 });
// Standalone timestamp index for time-range queries across all machines.
db.telemetry.createIndex({ timestamp: -1 });

// ─── purchase_orders ──────────────────────────────────────────────────────────
// Created by the Sourcing Agent when inventory.quantity = 0 in PostgreSQL.
// Status lifecycle: PENDING → ORDERED → DELIVERED
db.createCollection("purchase_orders", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["part_number", "part_name", "quantity_ordered", "status",
                 "triggered_by_work_order_id", "created_at"],
      properties: {
        part_number:              { bsonType: "string" },
        part_name:                { bsonType: "string" },
        quantity_ordered:         { bsonType: "int",
                                    minimum: 1 },
        status:                   { bsonType: "string",
                                    enum: ["PENDING", "ORDERED", "DELIVERED"] },
        triggered_by_work_order_id: { bsonType: "int",
                                      description: "FK to PostgreSQL work_orders.id" },
        created_at:               { bsonType: "date" },
        updated_at:               { bsonType: "date" }
      }
    }
  }
});

db.purchase_orders.createIndex({ status: 1 });
db.purchase_orders.createIndex({ part_number: 1 });
db.purchase_orders.createIndex({ triggered_by_work_order_id: 1 });

// ─── audit_logs ───────────────────────────────────────────────────────────────
// Immutable append-only log. Every agent action and system event is recorded here.
// Never update or delete — only insert.
db.createCollection("audit_logs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["event_type", "actor", "entity_type", "entity_id", "timestamp"],
      properties: {
        event_type:   { bsonType: "string",
                        description: "e.g. ANOMALY_DETECTED, WORK_ORDER_CREATED, PO_RAISED" },
        actor:        { bsonType: "string",
                        description: "e.g. triage_agent, sensor_service, scheduling_agent" },
        entity_type:  { bsonType: "string",
                        description: "e.g. machine, work_order, purchase_order" },
        entity_id:    { bsonType: "string",
                        description: "ID of the entity this event concerns" },
        payload:      { bsonType: "object",
                        description: "Arbitrary event detail — differs per event_type" },
        timestamp:    { bsonType: "date" }
      }
    }
  }
});

db.audit_logs.createIndex({ event_type: 1, timestamp: -1 });
db.audit_logs.createIndex({ entity_type: 1, entity_id: 1 });
db.audit_logs.createIndex({ actor: 1, timestamp: -1 });

// ─── Seed Data ────────────────────────────────────────────────────────────────
const now = new Date();

db.telemetry.insertMany([
  { machine_id: "CNC-01",   timestamp: now, sensor_type: "temperature", value: 72.4, unit: "celsius",  machine_status: "NORMAL" },
  { machine_id: "CNC-01",   timestamp: now, sensor_type: "vibration",   value: 1.2,  unit: "mm/s",     machine_status: "NORMAL" },
  { machine_id: "LATHE-01", timestamp: now, sensor_type: "rpm",         value: 1450, unit: "rpm",      machine_status: "NORMAL" },
  { machine_id: "PRESS-01", timestamp: now, sensor_type: "pressure",    value: 8.3,  unit: "bar",      machine_status: "DEGRADING" }
]);

db.purchase_orders.insertMany([
  {
    part_number: "PN-SEAL-004",
    part_name: "Oil Seal 40x60x10",
    quantity_ordered: NumberInt(10),
    status: "PENDING",
    triggered_by_work_order_id: NumberInt(0),
    created_at: now,
    updated_at: now
  }
]);

db.audit_logs.insertMany([
  {
    event_type:  "SYSTEM_INIT",
    actor:       "system",
    entity_type: "database",
    entity_id:   "amlo_db",
    payload:     { message: "MongoDB collections initialised" },
    timestamp:   now
  }
]);

print("MongoDB init complete: telemetry, purchase_orders, audit_logs ready.");
