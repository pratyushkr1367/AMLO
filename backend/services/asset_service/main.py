"""
Asset Service — Phase 4, AMLO
CRUD for machine/asset metadata stored in PostgreSQL.

Endpoints:
  GET   /machines                      — list all machines
  GET   /machines/{machine_id}         — get one machine
  PATCH /machines/{machine_id}/status  — update machine status

Run: python main.py
"""

from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from psycopg2 import pool
import uvicorn

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PORT

app = FastAPI(title="AMLO Asset Service")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

_pool = pool.ThreadedConnectionPool(
    1, 10,
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
    user=DB_USER, password=DB_PASSWORD
)

VALID_STATUSES = {"NORMAL", "DEGRADING", "CRITICAL", "OFFLINE"}


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
class StatusUpdate(BaseModel):
    status: str


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/machines")
def list_machines():
    with db() as cur:
        cur.execute("SELECT * FROM machines ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


@app.get("/machines/{machine_id}")
def get_machine(machine_id: str):
    with db() as cur:
        cur.execute("SELECT * FROM machines WHERE machine_id = %s", (machine_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Machine '{machine_id}' not found")
    return dict(row)


@app.patch("/machines/{machine_id}/status")
def update_status(machine_id: str, body: StatusUpdate):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_STATUSES}")
    with db() as cur:
        cur.execute(
            "UPDATE machines SET status = %s WHERE machine_id = %s RETURNING *",
            (body.status, machine_id)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Machine '{machine_id}' not found")
    return dict(row)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
