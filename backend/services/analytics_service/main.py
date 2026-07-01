"""
Analytics Service — AMLO
OEE metrics, downtime analytics, and predictive maintenance insights.

Endpoints:
  GET /analytics/oee         — Overall Equipment Effectiveness per machine
  GET /analytics/downtime    — Downtime events and duration per machine
  GET /analytics/predictive  — MTBF and next-failure predictions per machine
  GET /analytics/summary     — High-level factory health snapshot

Run: python main.py
"""

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

import psycopg2
import psycopg2.extras
from psycopg2 import pool
from pymongo import MongoClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, MONGO_URI, MONGO_DB, PORT

app = FastAPI(title="AMLO Analytics Service")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

_pool = pool.ThreadedConnectionPool(
    1, 5,
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


def _mongo():
    return MongoClient(MONGO_URI)[MONGO_DB]


def _get_machines() -> list[dict]:
    with db() as cur:
        cur.execute("SELECT id, machine_id, type AS machine_type, status FROM machines ORDER BY machine_id")
        return [dict(r) for r in cur.fetchall()]


def _get_work_orders() -> list[dict]:
    with db() as cur:
        cur.execute("SELECT machine_id, status, created_at, completed_at, fault_type FROM work_orders ORDER BY created_at")
        return [dict(r) for r in cur.fetchall()]


def _get_alerts(machine_id: str = None) -> list[dict]:
    mongo = _mongo()
    query = {"severity": "CRITICAL"}
    if machine_id:
        query["machine_id"] = machine_id
    docs = list(mongo.audit_logs.find(query, {"_id": 0}).sort("timestamp", 1))
    return docs


# ─── OEE Calculation ──────────────────────────────────────────────────────────
def _calc_oee(machine: dict, work_orders: list[dict], window_hours: int = 24) -> dict:
    machine_db_id = machine["id"]
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    # Incidents = completed work orders for this machine in the window
    incidents = [
        wo for wo in work_orders
        if wo["machine_id"] == machine_db_id
        and wo["status"] == "COMPLETED"
        and wo["completed_at"] is not None
        and wo["completed_at"] >= window_start
    ]

    total_seconds = window_hours * 3600

    # Downtime: estimate each incident as time from created_at to completed_at
    downtime_seconds = 0.0
    for wo in incidents:
        created   = wo["created_at"]
        completed = wo["completed_at"]
        if created and completed and completed > created:
            downtime_seconds += (completed - created).total_seconds()

    downtime_seconds = min(downtime_seconds, total_seconds)
    uptime_seconds   = total_seconds - downtime_seconds

    availability = uptime_seconds / total_seconds if total_seconds > 0 else 1.0
    # Performance and Quality default to 1.0 (no throughput/defect data available)
    performance  = 1.0
    quality      = 1.0
    oee          = availability * performance * quality

    return {
        "machine_id":         machine["machine_id"],
        "machine_type":       machine["machine_type"],
        "oee":                round(oee * 100, 1),
        "availability":       round(availability * 100, 1),
        "performance":        round(performance * 100, 1),
        "quality":            round(quality * 100, 1),
        "downtime_minutes":   round(downtime_seconds / 60, 1),
        "incidents":          len(incidents),
        "window_hours":       window_hours,
    }


# ─── Downtime Analytics ───────────────────────────────────────────────────────
def _calc_downtime(machine: dict, work_orders: list[dict]) -> dict:
    machine_db_id = machine["id"]
    now = datetime.now(timezone.utc)

    all_wos = [wo for wo in work_orders if wo["machine_id"] == machine_db_id]
    completed = [wo for wo in all_wos if wo["status"] == "COMPLETED" and wo["completed_at"]]
    open_wos  = [wo for wo in all_wos if wo["status"] in ("OPEN", "IN_PROGRESS")]

    incidents = []
    total_downtime = 0.0

    for wo in completed:
        duration = (wo["completed_at"] - wo["created_at"]).total_seconds()
        total_downtime += duration
        incidents.append({
            "fault_type": wo["fault_type"],
            "started_at": wo["created_at"].isoformat() if wo["created_at"] else None,
            "resolved_at": wo["completed_at"].isoformat(),
            "duration_minutes": round(duration / 60, 1),
            "status": "RESOLVED",
        })

    for wo in open_wos:
        duration = (now - wo["created_at"]).total_seconds() if wo["created_at"] else 0
        total_downtime += duration
        incidents.append({
            "fault_type": wo["fault_type"],
            "started_at": wo["created_at"].isoformat() if wo["created_at"] else None,
            "resolved_at": None,
            "duration_minutes": round(duration / 60, 1),
            "status": "ONGOING",
        })

    incidents.sort(key=lambda x: x["started_at"] or "", reverse=True)

    return {
        "machine_id":           machine["machine_id"],
        "machine_type":         machine["machine_type"],
        "total_incidents":      len(all_wos),
        "resolved_incidents":   len(completed),
        "ongoing_incidents":    len(open_wos),
        "total_downtime_hours": round(total_downtime / 3600, 2),
        "recent_incidents":     incidents[:5],
    }


# ─── Predictive Maintenance ───────────────────────────────────────────────────
def _calc_predictive(machine: dict, work_orders: list[dict]) -> dict:
    machine_db_id = machine["id"]
    completed = sorted(
        [wo for wo in work_orders if wo["machine_id"] == machine_db_id and wo["status"] == "COMPLETED"],
        key=lambda x: x["created_at"]
    )

    if len(completed) < 2:
        return {
            "machine_id":         machine["machine_id"],
            "machine_type":       machine["machine_type"],
            "mtbf_hours":         None,
            "last_failure":       completed[-1]["created_at"].isoformat() if completed else None,
            "next_failure_est":   None,
            "risk_level":         "UNKNOWN",
            "confidence":         "Low — insufficient history",
            "total_failures":     len(completed),
        }

    # MTBF = average gap between consecutive failures
    gaps = []
    for i in range(1, len(completed)):
        gap = (completed[i]["created_at"] - completed[i-1]["created_at"]).total_seconds() / 3600
        gaps.append(gap)
    mtbf_hours = sum(gaps) / len(gaps)

    last_failure = completed[-1]["created_at"]
    now          = datetime.now(timezone.utc)
    hours_since  = (now - last_failure).total_seconds() / 3600
    next_failure  = last_failure + timedelta(hours=mtbf_hours)

    overdue = hours_since > mtbf_hours
    risk = "HIGH" if overdue else ("MEDIUM" if hours_since > mtbf_hours * 0.7 else "LOW")

    return {
        "machine_id":         machine["machine_id"],
        "machine_type":       machine["machine_type"],
        "mtbf_hours":         round(mtbf_hours, 1),
        "last_failure":       last_failure.isoformat(),
        "next_failure_est":   next_failure.isoformat(),
        "hours_since_failure": round(hours_since, 1),
        "risk_level":         risk,
        "confidence":         f"Based on {len(completed)} incidents",
        "total_failures":     len(completed),
        "overdue":            overdue,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/analytics/oee")
def get_oee():
    machines    = _get_machines()
    work_orders = _get_work_orders()
    return [_calc_oee(m, work_orders) for m in machines]


@app.get("/analytics/downtime")
def get_downtime():
    machines    = _get_machines()
    work_orders = _get_work_orders()
    results = [_calc_downtime(m, work_orders) for m in machines]
    results.sort(key=lambda x: x["total_downtime_hours"], reverse=True)
    return results


@app.get("/analytics/predictive")
def get_predictive():
    machines    = _get_machines()
    work_orders = _get_work_orders()
    results = [_calc_predictive(m, work_orders) for m in machines]
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
    results.sort(key=lambda x: risk_order.get(x["risk_level"], 3))
    return results


@app.get("/analytics/summary")
def get_summary():
    machines    = _get_machines()
    work_orders = _get_work_orders()

    total_incidents  = len(work_orders)
    completed        = [wo for wo in work_orders if wo["status"] == "COMPLETED"]
    open_wos         = [wo for wo in work_orders if wo["status"] in ("OPEN", "IN_PROGRESS")]

    avg_resolution = None
    if completed:
        durations = [
            (wo["completed_at"] - wo["created_at"]).total_seconds() / 60
            for wo in completed if wo["completed_at"] and wo["created_at"]
        ]
        avg_resolution = round(sum(durations) / len(durations), 1) if durations else None

    oee_list  = [_calc_oee(m, work_orders) for m in machines]
    avg_oee   = round(sum(o["oee"] for o in oee_list) / len(oee_list), 1) if oee_list else 100.0

    predictive = [_calc_predictive(m, work_orders) for m in machines]
    high_risk  = [p for p in predictive if p["risk_level"] == "HIGH"]

    return {
        "total_machines":        len(machines),
        "total_incidents":       total_incidents,
        "open_incidents":        len(open_wos),
        "resolved_incidents":    len(completed),
        "avg_resolution_min":    avg_resolution,
        "avg_oee_pct":           avg_oee,
        "high_risk_machines":    len(high_risk),
        "high_risk_machine_ids": [p["machine_id"] for p in high_risk],
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
