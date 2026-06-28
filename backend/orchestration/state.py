from typing import TypedDict, Optional


class OrchestratorState(TypedDict):
    # ── Input (from anomaly event) ──────────────────────────
    machine_id: str
    machine_type: str
    sensor_type: str
    average_value: float
    severity: str

    # ── Triage output ───────────────────────────────────────
    diagnosis: Optional[dict]
    repair_steps: Optional[dict]

    # ── Sourcing output ─────────────────────────────────────
    parts_status: Optional[list]
    purchase_orders_created: Optional[list]

    # ── Scheduling output ───────────────────────────────────
    agv_id: Optional[str]
    agv_route: Optional[list]
    technician: Optional[dict]
    work_order_id: Optional[int]
