"""
AGV State Emulator — Phase 2, AMLO

Tracks grid position for each AGV. Exposes:
  GET  /agv/{id}/position   — current (row, col) and status
  GET  /agvs                — all AGVs
  POST /agv/{id}/dispatch   — walk a route step-by-step
  WS   /agv/{id}/ws         — live position stream (frontend)

Each step is also published to MQTT: amlo/agv/{agv_id}/position
The MQTT-Kafka Bridge forwards these to the agv-updates Kafka topic.

Run: python main.py
"""

import asyncio
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import uvicorn

from agv import AGV
from config import AGVS, STEP_INTERVAL, MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_PREFIX

app = FastAPI(title="AMLO AGV Emulator")

# ─── MQTT client ──────────────────────────────────────────────────────────────
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

# ─── State ────────────────────────────────────────────────────────────────────
agvs: dict[str, AGV] = {cfg["agv_id"]: AGV(**cfg) for cfg in AGVS}
connections: dict[str, list[WebSocket]] = {agv_id: [] for agv_id in agvs}
route_tasks: dict[str, asyncio.Task] = {}


# ─── WebSocket manager ────────────────────────────────────────────────────────
async def ws_connect(agv_id: str, ws: WebSocket):
    await ws.accept()
    connections[agv_id].append(ws)

def ws_disconnect(agv_id: str, ws: WebSocket):
    connections[agv_id].remove(ws)

async def broadcast(agv_id: str, data: dict):
    dead = []
    for ws in connections[agv_id]:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections[agv_id].remove(ws)


def publish_mqtt(agv: AGV):
    payload = {**agv.to_dict(), "timestamp": datetime.now(timezone.utc).isoformat()}
    topic = f"{MQTT_TOPIC_PREFIX}/{agv.agv_id}/position"
    mqtt_client.publish(topic, json.dumps(payload))


# ─── Route walker (background task) ──────────────────────────────────────────
async def walk_route(agv: AGV):
    publish_mqtt(agv)
    await broadcast(agv.agv_id, agv.to_dict())
    while agv.route:
        await asyncio.sleep(STEP_INTERVAL)
        done = agv.step()
        publish_mqtt(agv)
        await broadcast(agv.agv_id, agv.to_dict())
        if done:
            break
    print(f"[{agv.agv_id}] Route complete — parked at ({agv.row}, {agv.col})")


# ─── Models ───────────────────────────────────────────────────────────────────
class GridCell(BaseModel):
    row: int
    col: int

class DispatchRequest(BaseModel):
    route: list[GridCell]


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/agvs")
def list_agvs():
    return [agv.to_dict() for agv in agvs.values()]


@app.get("/agv/{agv_id}/position")
def get_position(agv_id: str):
    if agv_id not in agvs:
        raise HTTPException(status_code=404, detail=f"AGV '{agv_id}' not found")
    return agvs[agv_id].to_dict()


@app.post("/agv/{agv_id}/dispatch")
async def dispatch(agv_id: str, request: DispatchRequest):
    if agv_id not in agvs:
        raise HTTPException(status_code=404, detail=f"AGV '{agv_id}' not found")

    agv = agvs[agv_id]
    route = [{"row": cell.row, "col": cell.col} for cell in request.route]
    agv.dispatch(route)

    if agv_id in route_tasks and not route_tasks[agv_id].done():
        route_tasks[agv_id].cancel()

    route_tasks[agv_id] = asyncio.create_task(walk_route(agv))
    print(f"[{agv_id}] Dispatched on route of {len(route)} cells")
    return {"message": f"Dispatched {agv_id} on {len(route)}-cell route"}


@app.websocket("/agv/{agv_id}/ws")
async def websocket_endpoint(agv_id: str, websocket: WebSocket):
    if agv_id not in agvs:
        await websocket.close(code=1008)
        return

    await ws_connect(agv_id, websocket)
    await websocket.send_json(agvs[agv_id].to_dict())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_disconnect(agv_id, websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
