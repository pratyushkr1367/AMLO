"""
Inventory Service — Phase 4, AMLO
Spare parts stock management in PostgreSQL.

Endpoints:
  GET  /inventory                              — list all parts
  GET  /inventory/{part_number}               — get one part's stock level
  POST /inventory/{part_number}/decrement     — reduce quantity by N after a repair

Run: python main.py
"""

from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from psycopg2 import pool
import uvicorn

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PORT

app = FastAPI(title="AMLO Inventory Service")

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
class DecrementRequest(BaseModel):
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
            "UPDATE inventory SET quantity = quantity - %s WHERE part_number = %s RETURNING *",
            (body.quantity, part_number)
        )
        updated = cur.fetchone()
    return dict(updated)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
