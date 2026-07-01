"""
Scheduling Agent — Phase 7, AMLO

Node 3 of the orchestration graph.
  1. Runs A* to compute AGV route from its current position to the machine
  2. Dispatches the nearest available AGV via the AGV Emulator
  3. Assigns the best technician via the Technician Assignment Engine
  4. Creates a work order in the Work Order Service
"""

import sys
import os

_dsa = os.path.join(os.path.dirname(__file__), "..", "dsa")
if _dsa not in sys.path:
    sys.path.insert(0, _dsa)

import httpx
import pathfinding
import technician_assignment

from state import OrchestratorState

ASSET_URL    = "http://127.0.0.1:8002"
AGV_URL      = "http://127.0.0.1:8001"
LOGISTICS_URL = "http://127.0.0.1:8005"
WORK_ORDER_URL = "http://127.0.0.1:8004"

# Grid cell where an AGV parks to service each machine
# One cell to the right of each machine obstacle in pathfinding.DEFAULT_OBSTACLES
MACHINE_SERVICE_POS = {
    "CNC-01":   (5, 11),
    "CNC-02":   (5, 21),
    "LATHE-01": (15, 11),
    "LATHE-02": (15, 26),
    "PRESS-01": (25, 16),
    "WELD-01":  (35, 11),
    "WELD-02":  (35, 31),
}

# Grid position of the machine itself (for technician proximity scoring)
MACHINE_GRID_POS = {
    "CNC-01":   (5, 10),
    "CNC-02":   (5, 20),
    "LATHE-01": (15, 10),
    "LATHE-02": (15, 25),
    "PRESS-01": (25, 15),
    "WELD-01":  (35, 10),
    "WELD-02":  (35, 30),
}


def _get_machine_db_id(machine_id: str) -> int | None:
    """Return the integer PK of a machine by looking it up in the Asset Service."""
    try:
        machines = httpx.get(f"{ASSET_URL}/machines", timeout=5.0).json()
        for m in machines:
            if m.get("machine_id") == machine_id:
                return m["id"]
    except Exception:
        pass
    return None


def _nearest_agv(target: tuple) -> tuple[str, tuple]:
    """Return (agv_id, current_pos) for the AGV with shortest Manhattan distance to target."""
    try:
        agvs = httpx.get(f"{AGV_URL}/agvs", timeout=5.0).json()
        best_id, best_pos, best_d = "AGV-01", (0, 0), float("inf")
        for agv in agvs:
            pos = agv["position"]
            d = abs(pos["row"] - target[0]) + abs(pos["col"] - target[1])
            if d < best_d:
                best_d = d
                best_id = agv["id"]
                best_pos = (pos["row"], pos["col"])
        return best_id, best_pos
    except Exception:
        return "AGV-01", (0, 0)


def scheduling_node(state: OrchestratorState) -> dict:
    machine_id   = state["machine_id"]
    machine_type = state["machine_type"]
    target       = MACHINE_SERVICE_POS.get(machine_id, (25, 25))
    grid_pos     = MACHINE_GRID_POS.get(machine_id, (25, 25))

    print(f"\n[SCHEDULING] {machine_id} | target={target}")

    # ── 1. Compute route and dispatch AGV ────────────────────
    agv_id, agv_start = _nearest_agv(target)
    route = pathfinding.astar(agv_start, target) or []
    print(f"[SCHEDULING] Dispatching {agv_id} — {len(route)} steps from {agv_start}")
    try:
        httpx.post(f"{AGV_URL}/agv/{agv_id}/dispatch", json={"route": route}, timeout=5.0)
    except Exception as e:
        print(f"[SCHEDULING] AGV dispatch failed: {e}")

    # ── 2. Assign technician ──────────────────────────────────
    technician = technician_assignment.assign(machine_type, grid_pos[0], grid_pos[1])
    if technician:
        print(f"[SCHEDULING] Technician: {technician.get('name')} (id={technician.get('id')})")
        try:
            httpx.patch(
                f"{LOGISTICS_URL}/technicians/{technician['id']}/availability",
                json={"available": False},
                timeout=5.0,
            )
        except Exception as e:
            print(f"[SCHEDULING] Technician update failed: {e}")
    else:
        print("[SCHEDULING] No technician available")

    # ── 3. Create work order ──────────────────────────────────
    machine_db_id = _get_machine_db_id(machine_id)
    diagnosis = state.get("diagnosis") or {}
    repair    = state.get("repair_steps") or {}

    description = (
        f"{diagnosis.get('probable_cause', 'Fault detected')} on {machine_id}. "
        f"Confidence: {diagnosis.get('confidence', 'Unknown')}. "
        f"{diagnosis.get('recommended_action', '')}"
    )

    wo_payload = {
        "machine_id":    machine_db_id or 1,
        "fault_type":    diagnosis.get("probable_cause", "Unknown"),
        "description":   description,
        "priority":      "CRITICAL" if state["severity"] == "CRITICAL" else "HIGH",
        "technician_id": technician.get("id") if technician else None,
        "parts_used":    repair.get("parts_needed", []),
        "agv_route":     route,
    }

    work_order_id = None
    try:
        resp = httpx.post(f"{WORK_ORDER_URL}/work-orders", json=wo_payload, timeout=5.0)
        if resp.status_code == 201:
            work_order_id = resp.json().get("id")
            print(f"[SCHEDULING] Work order #{work_order_id} created")
    except Exception as e:
        print(f"[SCHEDULING] Work order creation failed: {e}")

    return {
        "agv_id":        agv_id,
        "agv_route":     route,
        "technician":    technician,
        "work_order_id": work_order_id,
    }
