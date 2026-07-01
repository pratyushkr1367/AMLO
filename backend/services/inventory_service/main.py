"""
Inventory Service — AMLO
Spare parts stock management in PostgreSQL.

Endpoints:
  GET  /inventory                          — list all parts
  GET  /inventory/{part_number}            — get one part's stock level
  POST /inventory/{part_number}/decrement  — reduce quantity after a repair
  POST /inventory/{part_number}/restock    — increase quantity (called by PO service)

Run: python main.py
"""

import threading
from contextlib import contextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from psycopg2 import pool
import uvicorn

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PORT

app = FastAPI(title="AMLO Inventory Service")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

PURCHASE_ORDER_URL = "http://127.0.0.1:8008"

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


def _notify_po_service(part_number: str, part_name: str, quantity: int, reorder_threshold: int):
    try:
        httpx.post(
            f"{PURCHASE_ORDER_URL}/purchase-orders/auto-check",
            json={
                "part_number":      part_number,
                "part_name":        part_name,
                "quantity":         quantity,
                "reorder_threshold": reorder_threshold,
            },
            timeout=3.0,
        )
    except Exception as e:
        print(f"[Inventory] Could not notify PO service: {e}")


# ─── Models ───────────────────────────────────────────────────────────────────
class QuantityRequest(BaseModel):
    quantity: int


# ─── Endpoints ────────────────────────────────────────────────────────────────
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
def decrement_stock(part_number: str, body: QuantityRequest):
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    with db() as cur:
        cur.execute("SELECT * FROM inventory WHERE part_number = %s", (part_number,))
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
        threading.Thread(
            target=_notify_po_service,
            args=(updated["part_number"], updated["part_name"],
                  updated["quantity"], updated["reorder_threshold"]),
            daemon=True
        ).start()

    return updated


@app.post("/inventory/{part_number}/restock")
def restock(part_number: str, body: QuantityRequest):
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    with db() as cur:
        cur.execute(
            "UPDATE inventory SET quantity = quantity + %s, updated_at = NOW() WHERE part_number = %s RETURNING *",
            (body.quantity, part_number)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Part '{part_number}' not found")
    return dict(row)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
