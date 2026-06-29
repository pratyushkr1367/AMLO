"""
Work Order Service — Phase 4, AMLO
Creates and manages maintenance tickets in PostgreSQL.

Endpoints:
  POST  /work-orders              — create a new work order
  GET   /work-orders              — list all work orders (filter by ?status=OPEN)
  GET   /work-orders/{id}         — get one work order
  PATCH /work-orders/{id}/status  — advance status through lifecycle

Run: python main.py
"""

import json
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from psycopg2 import pool
import uvicorn

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PORT

app = FastAPI(title="AMLO Work Order Service")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

_pool = pool.ThreadedConnectionPool(
    1, 10,
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
    user=DB_USER, password=DB_PASSWORD
)

VALID_STATUSES = {"OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


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
class CreateWorkOrder(BaseModel):
    machine_id: int
    technician_id: Optional[int] = None
    priority: str = "MEDIUM"
    fault_type: Optional[str] = None
    description: Optional[str] = None
    parts_used: list = []
    agv_route: list = []

class StatusUpdate(BaseModel):
    status: str


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/work-orders", status_code=201)
def create_work_order(body: CreateWorkOrder):
    if body.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Priority must be one of {VALID_PRIORITIES}")
    with db() as cur:
        cur.execute(
            """
            INSERT INTO work_orders
              (machine_id, technician_id, priority, fault_type, description, parts_used, agv_route)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                body.machine_id, body.technician_id, body.priority,
                body.fault_type, body.description,
                json.dumps(body.parts_used), json.dumps(body.agv_route)
            )
        )
        row = cur.fetchone()
    return dict(row)


@app.get("/work-orders")
def list_work_orders(status: Optional[str] = Query(default=None)):
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_STATUSES}")
    with db() as cur:
        if status:
            cur.execute(
                "SELECT * FROM work_orders WHERE status = %s ORDER BY created_at DESC",
                (status,)
            )
        else:
            cur.execute("SELECT * FROM work_orders ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.get("/work-orders/{work_order_id}")
def get_work_order(work_order_id: int):
    with db() as cur:
        cur.execute("SELECT * FROM work_orders WHERE id = %s", (work_order_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Work order {work_order_id} not found")
    return dict(row)


@app.patch("/work-orders/{work_order_id}/status")
def update_status(work_order_id: int, body: StatusUpdate):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_STATUSES}")
    with db() as cur:
        cur.execute(
            """
            UPDATE work_orders
            SET status = %s,
                completed_at = CASE WHEN %s = 'COMPLETED' THEN NOW() ELSE completed_at END
            WHERE id = %s
            RETURNING *
            """,
            (body.status, body.status, work_order_id)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Work order {work_order_id} not found")
    return dict(row)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
