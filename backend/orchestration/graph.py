"""
LangGraph State Machine — Phase 7, AMLO

Wires the three agent nodes into a linear graph:
  triage → sourcing → scheduling → END

Exposes run_orchestration(anomaly_event) for external callers.
"""

from langgraph.graph import StateGraph, END

from state import OrchestratorState
from triage import triage_node
from sourcing import sourcing_node
from scheduling import scheduling_node


def _build():
    g = StateGraph(OrchestratorState)
    g.add_node("triage", triage_node)
    g.add_node("sourcing", sourcing_node)
    g.add_node("scheduling", scheduling_node)
    g.set_entry_point("triage")
    g.add_edge("triage", "sourcing")
    g.add_edge("sourcing", "scheduling")
    g.add_edge("scheduling", END)
    return g.compile()


_app = _build()


def run_orchestration(anomaly_event: dict) -> dict:
    """
    Trigger the full agent pipeline for an anomaly.

    anomaly_event keys:
      machine_id, machine_type, sensor_type, average_value, severity
    """
    initial: OrchestratorState = {
        "machine_id":              anomaly_event["machine_id"],
        "machine_type":            anomaly_event.get("machine_type", ""),
        "sensor_type":             anomaly_event["sensor_type"],
        "average_value":           float(anomaly_event["average_value"]),
        "severity":                anomaly_event["severity"],
        "diagnosis":               None,
        "repair_steps":            None,
        "parts_status":            None,
        "purchase_orders_created": None,
        "agv_id":                  None,
        "agv_route":               None,
        "technician":              None,
        "work_order_id":           None,
    }
    return _app.invoke(initial)
