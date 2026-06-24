"""
Notification Service — Phase 4, AMLO
Broadcasts live alerts over WebSocket and logs every event to MongoDB audit_logs.

Endpoints:
  POST /notify       — receive an alert, broadcast to WS clients, log to MongoDB
  WS   /ws/alerts    — frontend connects here to receive live alerts

Run: python main.py
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pymongo import MongoClient
import uvicorn

from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION, PORT

app = FastAPI(title="AMLO Notification Service")

# MongoDB
_mongo = MongoClient(MONGO_URI)
audit_logs = _mongo[MONGO_DB][MONGO_COLLECTION]

# Connected WebSocket clients
_clients: list[WebSocket] = []


# ─── Models ───────────────────────────────────────────────────────────────────
class Alert(BaseModel):
    event_type: str          # e.g. ANOMALY_DETECTED, WORK_ORDER_CREATED
    actor: str               # e.g. triage_agent, sensor_service
    entity_type: str         # e.g. machine, work_order
    entity_id: str           # ID of the affected entity
    payload: dict[str, Any] = {}


# ─── WebSocket manager ────────────────────────────────────────────────────────
async def broadcast(data: dict):
    dead = []
    for ws in _clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.remove(ws)


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/notify")
async def notify(alert: Alert):
    doc = {
        **alert.model_dump(),
        "timestamp": datetime.now(timezone.utc)
    }

    # Log to MongoDB
    audit_logs.insert_one(doc)

    # Broadcast to all connected WebSocket clients
    doc["timestamp"] = doc["timestamp"].isoformat()
    await broadcast(doc)

    print(f"[{doc['event_type']}] {doc['actor']} → {doc['entity_type']}:{doc['entity_id']}")
    return {"status": "sent", "clients_notified": len(_clients)}


@app.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await websocket.accept()
    _clients.append(websocket)
    print(f"WebSocket client connected — total: {len(_clients)}")
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        _clients.remove(websocket)
        print(f"WebSocket client disconnected — total: {len(_clients)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
