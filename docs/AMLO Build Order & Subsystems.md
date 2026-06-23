# AMLO — Subsystems & Build Order (With Emulators)

## Updated Subsystem List

| Layer | Subsystems |
|---|---|
| **1. Emulation Layer** *(new)* | IoT Sensor Emulator, AGV State Emulator |
| **2. Data Ingestion** | Kafka Broker, Kafka Producer (in emulator), Kafka Consumer (Sensor Service) |
| **3. Data Storage** | PostgreSQL (assets, inventory, work orders, technicians), MongoDB (telemetry, audit logs, POs), pgvector (manuals, SOPs) |
| **4. FastAPI Microservices** | Sensor Service, Asset Service, Inventory Service, Logistics Service, Work Order Service, Notification Service |
| **5. Analytics & DSA Engine** | Sliding Window Anomaly Detector (Circular Queue), Priority Scoring Engine, Custom Min-Heap, A\* Pathfinding Engine, Technician Assignment Engine |
| **6. RAG + LLM** | Document Embedding Pipeline, pgvector Semantic Search, LLM Integration (root cause, repair instructions, work order drafting) |
| **7. Agentic Orchestration** | LangGraph State Machine, Triage Agent, Sourcing Agent, Scheduling Agent |
| **8. Presentation** | Next.js Dashboard, Factory Floor Grid Map, Live Alerts Panel, OEE Metrics, AGV Tracking View, Inventory View, Work Orders View, Analytics View |

---

## What the Two Emulators Look Like

**IoT Sensor Emulator**
- Models N machines (CNC-01, CNC-02, Lathe-01, etc.), each with its own state: `NORMAL → DEGRADING → CRITICAL`
- Each tick generates readings for temp, vibration, pressure, RPM within realistic ranges per state
- Has a configurable anomaly injection scheduler (e.g. every 60s, randomly push one machine into `CRITICAL`)
- Publishes each reading as a JSON event to a Kafka topic (`sensor-events`)

**AGV State Emulator**
- Maintains a position `(row, col)` for each AGV on the 50×50 grid
- Exposes an endpoint: `POST /agv/{id}/dispatch` that accepts a route (list of grid cells from A\*)
- Walks the route step-by-step on a timer, broadcasting position updates via WebSocket
- Also exposes a `GET /agv/{id}/position` for the dashboard to poll

---

## Build Order

### Phase 1 — Data Foundation
1. **PostgreSQL schema** — machines, inventory, technicians, work orders
2. **MongoDB collections** — telemetry, purchase orders, audit logs
3. **pgvector setup** — extension enabled, `document_chunks` table with embedding column
4. **Document ingestion script** — chunks and embeds sample PDF manuals into pgvector

*Everything else is a consumer of these. Schema changes later are painful — nail this first.*

---

### Phase 2 — Emulation Layer
5. **IoT Sensor Emulator**
   - Machine state models + realistic value ranges per sensor type
   - Anomaly injection on a configurable schedule
   - Kafka producer that publishes `sensor-events` JSON payloads
6. **AGV State Emulator**
   - Grid position state per AGV (hardcoded starting positions)
   - `/dispatch` endpoint accepts a route array and walks it on a timer
   - WebSocket broadcaster for live position updates
   - At this stage, dispatch it a hardcoded dummy route — A\* comes later

*Build emulators before microservices so you have real data flowing from day one. Every service you build after this can be tested with live emulated events.*

---

### Phase 3 — Data Ingestion Pipeline
7. **Kafka broker setup** — topics: `sensor-events`, `alerts`, `agv-updates`
8. **Sensor Service** — Kafka consumer that reads `sensor-events` and writes raw telemetry to MongoDB

*Keep this thin. Sensor Service only persists — anomaly detection happens in Phase 4.*

---

### Phase 4 — Core Microservices
9. **Asset Service** — CRUD for machine/asset metadata (PostgreSQL)
10. **Inventory Service** — stock queries and decrement on use (PostgreSQL)
11. **Work Order Service** — create, update, retrieve maintenance tickets (PostgreSQL)
12. **Logistics Service** — wraps AGV Emulator dispatch + technician data queries
13. **Notification Service** — pushes alerts to WebSocket clients and logs to MongoDB

*These are the tools that agents call. Build and REST-test each one independently before touching agents.*

---

### Phase 5 — Analytics & DSA Engine
14. **Circular Queue** — core data structure, unit-tested in isolation
15. **Sliding Window Anomaly Detector** — wraps the Circular Queue, subscribes to Sensor Service output, emits anomaly events when thresholds are crossed
16. **Priority Scoring Engine** — scores simultaneous incidents by revenue/safety/production impact
17. **Custom Min-Heap** — standalone data structure, unit-tested
18. **A\* Pathfinding Engine** — uses the Min-Heap, operates on the 50×50 grid, returns an ordered list of cells
19. **Technician Assignment Engine** — skill + proximity + availability scoring against PostgreSQL technician records

*Wire A\* to the AGV Emulator here — replace the dummy hardcoded route with a real computed path.*

---

### Phase 6 — RAG + LLM Layer
20. **Semantic vector search** — query pgvector by embedding, return top-K chunks
21. **LLM integration** — connect to Claude API, pass retrieved chunks as context
22. **Root cause analysis prompt** — given anomaly data + manual chunks, output probable fault + confidence
23. **Repair instruction generation** — torque specs, steps, safety notes from manual chunks
24. **Work order drafting** — structured JSON work order generated by LLM

*Test each prompt independently with canned inputs before wiring into agents.*

---

### Phase 7 — Agentic Orchestration
25. **LangGraph State Machine** — define graph nodes, edges, and shared state schema
26. **Triage Agent** — node: receives anomaly → calls RAG → calls LLM → outputs diagnosis
27. **Sourcing Agent** — node: reads parts from diagnosis → queries Inventory Service → if stock = 0, creates PO in MongoDB
28. **Scheduling Agent** — node: calls A\* via Logistics Service → dispatches AGV Emulator → assigns technician → triggers Work Order Service

*At this point the full E2E loop is working: emulated sensor spike → Kafka → anomaly → agents → work order → AGV dispatched.*

---

### Phase 8 — Presentation Layer
29. **Next.js project setup + WebSocket client**
30. **Factory Floor Grid Map** — 50×50 grid, machine health colored by state, AGV position overlaid from emulator WebSocket feed
31. **Live Alerts Panel** — real-time incident feed via WebSocket from Notification Service
32. **Work Orders View** — list and detail of generated tickets
33. **Inventory View** — stock levels and purchase orders from MongoDB
34. **OEE Metrics Dashboard** — availability, performance, quality KPIs computed from telemetry
35. **Analytics / Executive View** — downtime trends, incident history

*Build the frontend last — by now every data source is real and live, so what you see is the actual system working.*

---

## Critical Dependency Chain

```
Storage → Emulators → Kafka → Microservices → DSA → RAG → Agents → Frontend
```

The emulators sit in Phase 2, immediately after storage, so you are never blocked waiting for real hardware data.
