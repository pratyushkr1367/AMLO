"""
Inventory Service — Phase 4, AMLO
Spare parts stock management in PostgreSQL.

Endpoints:
  GET  /inventory                              — list all parts
  GET  /inventory/{part_number}               — get one part's stock level
  POST /inventory/{part_number}/decrement     — reduce quantity by N after a repair
  GET  /purchase-orders                       — list POs (filter ?status=OPEN|PROCESSING|COMPLETED)
  POST /purchase-orders                       — create a PO manually
  PATCH /purchase-orders/{id}/approve         — approve a PO (10s delay → inventory updated)

Run: python main.py
"""

import threading
import time
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

app = FastAPI(title="AMLO Inventory Service")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

_pool = pool.ThreadedConnectionPool(
    1, 10,
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
    user=DB_USER, password=DB_PASSWORD
)

MAX_STOCK_MULTIPLIER = 5  # max_stock = reorder_threshold * 5


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
    print("[Inventory] purchase_orders table ready")


def _auto_create_pos():
    """Create POs for any inventory item at or below reorder threshold with no pending PO."""
    try:
        with db() as cur:
            cur.execute("SELECT part_number, part_name, quantity, reorder_threshold FROM inventory")
            items = [dict(r) for r in cur.fetchall()]

        for item in items:
            if item["quantity"] <= item["reorder_threshold"]:
                with db() as cur:
                    cur.execute(
                        "SELECT id FROM purchase_orders WHERE part_number = %s AND status IN ('OPEN', 'PROCESSING')",
                        (item["part_number"],)
                    )
                    if cur.fetchone():
                        continue  # already has a pending PO

                max_stock = item["reorder_threshold"] * MAX_STOCK_MULTIPLIER
                qty_to_order = max(1, max_stock - item["quantity"])
                with db() as cur:
                    cur.execute(
                        """INSERT INTO purchase_orders
                           (part_number, part_name, quantity_ordered, quantity_at_order, reorder_threshold, max_stock)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (item["part_number"], item["part_name"], qty_to_order,
                         item["quantity"], item["reorder_threshold"], max_stock)
                    )
                print(f"[Inventory] Auto-PO created: {item['part_number']} × {qty_to_order}")
    except Exception as e:
        print(f"[Inventory] Auto-PO check failed: {e}")


def _auto_po_loop():
    time.sleep(5)  # let the service start before first check
    while True:
        _auto_create_pos()
        time.sleep(60)


def _complete_po(po_id: int, part_number: str, quantity_ordered: int):
    time.sleep(5)
    try:
        with db() as cur:
            cur.execute(
                "UPDATE inventory SET quantity = quantity + %s, updated_at = NOW() WHERE part_number = %s",
                (quantity_ordered, part_number)
            )
        with db() as cur:
            cur.execute(
                "UPDATE purchase_orders SET status = 'COMPLETED', completed_at = NOW() WHERE id = %s",
                (po_id,)
            )
        print(f"[Inventory] PO #{po_id} completed — added {quantity_ordered} × {part_number}")
    except Exception as e:
        print(f"[Inventory] PO completion failed: {e}")


@app.on_event("startup")
def startup():
    _init_tables()
    threading.Thread(target=_auto_po_loop, daemon=True).start()


# ─── Models ───────────────────────────────────────────────────────────────────
class DecrementRequest(BaseModel):
    quantity: int

class CreatePORequest(BaseModel):
    part_number: str
    quantity_ordered: int


# ─── Inventory Endpoints ──────────────────────────────────────────────────────
@app.get("/inventory")
def list_inventory():
    with db() as cur:
        cur.execute("SELECT * FROM inventory ORDER BY part_number")
        return [dict(r) for r in cur.fetchall()]


@app.get("/inventory/{part_number}")
def get_part(part_number: str):
    with db() as cur:
        cur.execute("SELECT * FROM inventory WHERE part_number = %s", (part_number,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Part '{part_number}' not found")
    return dict(row)


@app.post("/inventory/{part_number}/decrement")
def decrement_stock(part_number: str, body: DecrementRequest):
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    with db() as cur:
        cur.execute("SELECT quantity FROM inventory WHERE part_number = %s", (part_number,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Part '{part_number}' not found")
        if row["quantity"] < body.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock: have {row['quantity']}, need {body.quantity}"
            )
        cur.execute(
            "UPDATE inventory SET quantity = quantity - %s, updated_at = NOW() WHERE part_number = %s RETURNING *",
            (body.quantity, part_number)
        )
        updated = dict(cur.fetchone())

    if updated["quantity"] <= updated["reorder_threshold"]:
        threading.Thread(target=_auto_create_pos, daemon=True).start()

    return updated


# ─── Purchase Order Endpoints ─────────────────────────────────────────────────
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
    with db() as cur:
        cur.execute("SELECT part_name, quantity, reorder_threshold FROM inventory WHERE part_number = %s", (body.part_number,))
        item = cur.fetchone()
    if not item:
        raise HTTPException(status_code=404, detail=f"Part '{body.part_number}' not found")
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
    return {"id": po_id, "status": "PROCESSING", "message": "Inventory will update in 10 seconds"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
