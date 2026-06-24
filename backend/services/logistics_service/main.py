"""
Logistics Service — Phase 4, AMLO
Dispatches AGVs and finds available technicians.

Endpoints:
  POST /dispatch-agv              — send an AGV to a destination via the AGV Emulator
  GET  /technicians/available     — list available technicians, optional ?skill= filter

Run: python main.py
"""

from contextlib import contextmanager
from typing import Optional

import httpx
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, AGV_EMULATOR_URL, PORT

app = FastAPI(title="AMLO Logistics Service")

_pool = pool.ThreadedConnectionPool(
    1, 10,
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
    user=DB_USER, password=DB_PASSWORD
)


@contextmanager
def db():
    conn = _pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _pool.putconn(conn)


# ─── Models ───────────────────────────────────────────────────────────────────
class GridCell(BaseModel):
    row: int
    col: int

class DispatchRequest(BaseModel):
    agv_id: str
    route: list[GridCell]


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/dispatch-agv")
def dispatch_agv(body: DispatchRequest):
    payload = {"route": [cell.model_dump() for cell in body.route]}
    try:
        response = httpx.post(
            f"{AGV_EMULATOR_URL}/agv/{body.agv_id}/dispatch",
            json=payload,
            timeout=5.0
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"AGV Emulator error: {e.response.text}")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="AGV Emulator is unreachable")
    return response.json()


@app.get("/technicians/available")
def get_available_technicians(skill: Optional[str] = Query(default=None)):
    with db() as cur:
        if skill:
            # Check if skill exists anywhere in the skills TEXT[] array
            cur.execute(
                "SELECT * FROM technicians WHERE availability = 'AVAILABLE' AND %s = ANY(skills) ORDER BY id",
                (skill,)
            )
        else:
            cur.execute(
                "SELECT * FROM technicians WHERE availability = 'AVAILABLE' ORDER BY id"
            )
        return [dict(r) for r in cur.fetchall()]


@app.get("/technicians/{technician_id}")
def get_technician(technician_id: int):
    with db() as cur:
        cur.execute("SELECT * FROM technicians WHERE id = %s", (technician_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Technician {technician_id} not found")
    return dict(row)


@app.patch("/technicians/{technician_id}/availability")
def update_availability(technician_id: int, body: dict):
    valid = {"AVAILABLE", "BUSY", "OFF_SHIFT"}
    availability = body.get("availability")
    if availability not in valid:
        raise HTTPException(status_code=400, detail=f"Availability must be one of {valid}")
    with db() as cur:
        cur.execute(
            "UPDATE technicians SET availability = %s WHERE id = %s RETURNING *",
            (availability, technician_id)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Technician {technician_id} not found")
    return dict(row)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
