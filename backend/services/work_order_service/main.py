"""
Work Order Service — Phase 4, AMLO
Creates and manages maintenance tickets in PostgreSQL.

Endpoints:
  POST  /work-orders              — create a new work order (auto-completes in 20s if parts stocked)
  GET   /work-orders              — list all work orders (filter by ?status=OPEN|IN_PROGRESS|COMPLETED)
  GET   /work-orders/{id}         — get one work order
  PATCH /work-orders/{id}/status  — manually advance status

Run: python main.py
"""

import json
import threading
import time
from contextlib import contextmanager
from typing import Optional

import httpx
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

VALID_STATUSES   = {"OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
INVENTORY_URL    = "http://127.0.0.1:8003"
FALLBACK_FAULT   = "Sensor anomaly detected — LLM unavailable (rate limit)"

_in_flight: set[int] = set()  # work order IDs currently being auto-processed


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


def _set_status(wo_id: int, status: str):
    with db() as cur:
        cur.execute(
            """UPDATE work_orders
               SET status = %s,
                   completed_at = CASE WHEN %s = 'COMPLETED' THEN NOW() ELSE completed_at END
               WHERE id = %s""",
            (status, status, wo_id)
        )


def _check_and_deduct_parts(parts_used: list) -> bool:
    """Return True if all known parts are sufficiently stocked. Unknown part numbers are skipped."""
    for part in parts_used:
        if not isinstance(part, dict):
            continue
        pn  = part.get("part_number")
        qty = _safe_qty(part.get("quantity", 1))
        if not pn:
            continue
        try:
            r = httpx.get(f"{INVENTORY_URL}/inventory/{pn}", timeout=3.0)
            if r.status_code == 404:
                continue  # part not in our inventory — skip, don't block
            if r.status_code != 200 or r.json().get("quantity", 0) < qty:
                return False
        except Exception:
            continue  # inventory unreachable — don't block WO indefinitely
    return True


def _deduct_parts(parts_used: list):
    for part in parts_used:
        if not isinstance(part, dict):
            continue
        pn  = part.get("part_number")
        qty = _safe_qty(part.get("quantity", 1))
        if not pn:
            continue
        try:
            r = httpx.post(
                f"{INVENTORY_URL}/inventory/{pn}/decrement",
                json={"quantity": qty},
                timeout=3.0
            )
            if r.status_code == 404:
                print(f"[WorkOrder] Part {pn} not in inventory — skipping deduction")
        except Exception as e:
            print(f"[WorkOrder] Failed to deduct {pn}: {e}")


def _auto_complete(wo_id: int, parts_used: list):
    """Background: set IN_PROGRESS immediately, wait 20s, deduct parts, set COMPLETED."""
    _set_status(wo_id, "IN_PROGRESS")
    print(f"[WorkOrder] #{wo_id} → IN_PROGRESS (auto, parts available)")
    time.sleep(5)
    _deduct_parts(parts_used)
    _set_status(wo_id, "COMPLETED")
    _in_flight.discard(wo_id)
    print(f"[WorkOrder] #{wo_id} → COMPLETED (auto)")


def _safe_parse_parts(parts_used) -> list:
    if isinstance(parts_used, list):
        return parts_used
    if isinstance(parts_used, str):
        try:
            return json.loads(parts_used)
        except Exception:
            return []
    return []


def _safe_qty(value) -> int:
    """Extract an integer quantity from values like 1, '2', '10g per bearing'."""
    try:
        return int(value)
    except (TypeError, ValueError):
        import re
        m = re.match(r'\d+', str(value))
        return int(m.group()) if m else 1


def _poll_open_work_orders():
    """Periodically pick up OPEN work orders and recover orphaned IN_PROGRESS ones."""
    time.sleep(5)  # let the service fully start
    while True:
        try:
            with db() as cur:
                cur.execute(
                    "SELECT id, fault_type, parts_used, status FROM work_orders WHERE status IN ('OPEN', 'IN_PROGRESS')"
                )
                rows = [dict(r) for r in cur.fetchall()]

            # Recover IN_PROGRESS WOs not tracked in _in_flight (service restarted mid-run)
            for row in rows:
                if row["status"] == "IN_PROGRESS" and row["id"] not in _in_flight:
                    print(f"[WorkOrder] Recovering orphaned IN_PROGRESS #{row['id']}")
                    _in_flight.add(row["id"])
                    parts = _safe_parse_parts(row["parts_used"])
                    threading.Thread(target=_auto_complete, args=(row["id"], parts), daemon=True).start()

            for row in [r for r in rows if r["status"] == "OPEN"]:
                wo_id = row["id"]
                if wo_id in _in_flight:
                    continue
                if row.get("fault_type") == FALLBACK_FAULT:
                    continue  # wait for LLM retry before processing
                parts = _safe_parse_parts(row["parts_used"])
                # No parts needed → complete without deduction
                # Parts listed → check inventory first
                if not parts or _check_and_deduct_parts(parts):
                    _in_flight.add(wo_id)
                    threading.Thread(target=_auto_complete, args=(wo_id, parts), daemon=True).start()
        except Exception as e:
            print(f"[WorkOrder] Poll error: {e}")
        time.sleep(5)  # check every 5 seconds


@app.on_event("startup")
def startup():
    threading.Thread(target=_poll_open_work_orders, daemon=True).start()


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

class DiagnosisUpdate(BaseModel):
    fault_type: str
    description: str
    parts_used: list = []


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
                (body.fault_type or "")[:100], body.description,
                json.dumps(body.parts_used), json.dumps(body.agv_route)
            )
        )
        row = cur.fetchone()
    wo = dict(row)

    # Auto-complete: skip fallback WOs — wait for real LLM diagnosis first
    parts = body.parts_used
    if wo["id"] not in _in_flight and body.fault_type != FALLBACK_FAULT and (not parts or _check_and_deduct_parts(parts)):
        _in_flight.add(wo["id"])
        threading.Thread(target=_auto_complete, args=(wo["id"], parts), daemon=True).start()

    return wo


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


@app.delete("/work-orders")
def delete_all_work_orders():
    with db() as cur:
        cur.execute("DELETE FROM work_orders")
        cur.execute("SELECT COUNT(*) FROM work_orders")
    _in_flight.clear()
    return {"deleted": True}


@app.patch("/work-orders/{work_order_id}/diagnosis")
def update_diagnosis(work_order_id: int, body: DiagnosisUpdate):
    with db() as cur:
        cur.execute(
            """UPDATE work_orders
               SET fault_type = %s, description = %s, parts_used = %s
               WHERE id = %s AND status = 'OPEN'
               RETURNING id""",
            (body.fault_type[:100], body.description, json.dumps(body.parts_used), work_order_id)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Work order not found or not in OPEN status")
    return {"id": work_order_id, "updated": True}


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
