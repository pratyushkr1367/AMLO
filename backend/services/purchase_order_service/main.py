"""
Purchase Order Service — AMLO
Manages procurement of spare parts in PostgreSQL.

Endpoints:
  GET  /purchase-orders                  — list all POs (filter ?status=OPEN|PROCESSING|COMPLETED)
  POST /purchase-orders                  — create a PO manually
  POST /purchase-orders/auto-check       — triggered by inventory service on stock drop
  PATCH /purchase-orders/{id}/approve    — approve a PO (5s delay → inventory restocked)

Run: python main.py
"""

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

app = FastAPI(title="AMLO Purchase Order Service")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

INVENTORY_URL        = "http://127.0.0.1:8003"
MAX_STOCK_MULTIPLIER = 5

_auto_approve = False  # toggled at runtime

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


def _init_tables():
    with db() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id               SERIAL PRIMARY KEY,
                part_number      VARCHAR(100) NOT NULL,
                part_name        VARCHAR(200) NOT NULL,
                quantity_ordered INT NOT NULL,
                quantity_at_order INT NOT NULL,
                reorder_threshold INT NOT NULL,
                max_stock        INT NOT NULL,
                status           VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                approved_at      TIMESTAMPTZ,
                completed_at     TIMESTAMPTZ
            )
        """)
    print("[PurchaseOrder] purchase_orders table ready")


def _has_pending_po(part_number: str) -> bool:
    with db() as cur:
        cur.execute(
            "SELECT id FROM purchase_orders WHERE part_number = %s AND status IN ('OPEN', 'PROCESSING')",
            (part_number,)
        )
        return cur.fetchone() is not None


def _create_po_for_item(item: dict):
    global _auto_approve
    if _has_pending_po(item["part_number"]):
        return
    max_stock    = item["reorder_threshold"] * MAX_STOCK_MULTIPLIER
    qty_to_order = max(1, max_stock - item["quantity"])
    with db() as cur:
        cur.execute(
            """INSERT INTO purchase_orders
               (part_number, part_name, quantity_ordered, quantity_at_order, reorder_threshold, max_stock)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (item["part_number"], item["part_name"], qty_to_order,
             item["quantity"], item["reorder_threshold"], max_stock)
        )
        po_id = cur.fetchone()["id"]
    print(f"[PurchaseOrder] Auto-PO created: {item['part_number']} × {qty_to_order}")

    if _auto_approve:
        with db() as cur:
            cur.execute(
                "UPDATE purchase_orders SET status = 'PROCESSING', approved_at = NOW() WHERE id = %s",
                (po_id,)
            )
        threading.Thread(target=_complete_po, args=(po_id, item["part_number"], qty_to_order), daemon=True).start()
        print(f"[PurchaseOrder] Auto-approved PO #{po_id}")


def _scan_all_inventory():
    """Check all inventory items and create POs for any below reorder threshold."""
    try:
        r = httpx.get(f"{INVENTORY_URL}/inventory", timeout=5.0)
        if r.status_code != 200:
            return
        for item in r.json():
            if item["quantity"] <= item["reorder_threshold"]:
                _create_po_for_item(item)
    except Exception as e:
        print(f"[PurchaseOrder] Inventory scan failed: {e}")


def _auto_po_loop():
    time.sleep(5)
    while True:
        _scan_all_inventory()
        time.sleep(60)


def _complete_po(po_id: int, part_number: str, quantity_ordered: int):
    time.sleep(5)
    try:
        httpx.post(
            f"{INVENTORY_URL}/inventory/{part_number}/restock",
            json={"quantity": quantity_ordered},
            timeout=5.0,
        )
        with db() as cur:
            cur.execute(
                "UPDATE purchase_orders SET status = 'COMPLETED', completed_at = NOW() WHERE id = %s",
                (po_id,)
            )
        print(f"[PurchaseOrder] PO #{po_id} completed — restocked {quantity_ordered} × {part_number}")
    except Exception as e:
        print(f"[PurchaseOrder] PO completion failed: {e}")


@app.on_event("startup")
def startup():
    _init_tables()
    threading.Thread(target=_auto_po_loop, daemon=True).start()


# ─── Models ───────────────────────────────────────────────────────────────────
class CreatePORequest(BaseModel):
    part_number: str
    quantity_ordered: int

class AutoCheckRequest(BaseModel):
    part_number: str
    part_name: str
    quantity: int
    reorder_threshold: int


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/purchase-orders/approval-mode")
def get_approval_mode():
    return {"mode": "auto" if _auto_approve else "manual"}


@app.post("/purchase-orders/approval-mode")
def set_approval_mode(body: dict):
    global _auto_approve
    mode = body.get("mode", "manual")
    if mode not in ("manual", "auto"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="mode must be 'manual' or 'auto'")
    _auto_approve = mode == "auto"
    print(f"[PurchaseOrder] Approval mode set to: {mode}")
    return {"mode": mode}


@app.get("/purchase-orders")
def list_pos(status: Optional[str] = Query(default=None)):
    with db() as cur:
        if status:
            cur.execute(
                "SELECT * FROM purchase_orders WHERE status = %s ORDER BY created_at DESC",
                (status,)
            )
        else:
            cur.execute("SELECT * FROM purchase_orders ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


@app.post("/purchase-orders", status_code=201)
def create_po(body: CreatePORequest):
    r = httpx.get(f"{INVENTORY_URL}/inventory/{body.part_number}", timeout=5.0)
    if r.status_code != 200:
        raise HTTPException(status_code=404, detail=f"Part '{body.part_number}' not found")
    item = r.json()
    max_stock = item["reorder_threshold"] * MAX_STOCK_MULTIPLIER
    with db() as cur:
        cur.execute(
            """INSERT INTO purchase_orders
               (part_number, part_name, quantity_ordered, quantity_at_order, reorder_threshold, max_stock)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (body.part_number, item["part_name"], body.quantity_ordered,
             item["quantity"], item["reorder_threshold"], max_stock)
        )
        row = cur.fetchone()
    return dict(row)


@app.post("/purchase-orders/auto-check", status_code=200)
def auto_check(body: AutoCheckRequest):
    """Called by inventory service immediately after a decrement drops stock to/below threshold."""
    threading.Thread(target=_create_po_for_item, args=(body.dict(),), daemon=True).start()
    return {"queued": True}


@app.patch("/purchase-orders/{po_id}/approve")
def approve_po(po_id: int):
    with db() as cur:
        cur.execute(
            "UPDATE purchase_orders SET status = 'PROCESSING', approved_at = NOW() WHERE id = %s AND status = 'OPEN' RETURNING *",
            (po_id,)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="PO not found or not in OPEN status")
    po = dict(row)
    threading.Thread(
        target=_complete_po,
        args=(po_id, po["part_number"], po["quantity_ordered"]),
        daemon=True
    ).start()
    return {"id": po_id, "status": "PROCESSING", "message": "Inventory will restock in 5 seconds"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
