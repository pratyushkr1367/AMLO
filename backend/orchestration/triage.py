"""
Triage Agent — Phase 7, AMLO

Node 1 of the orchestration graph.
Receives an anomaly event, queries the RAG pipeline, and produces:
  - diagnosis  : probable cause, confidence, reasoning, recommended action
  - repair_steps : ordered steps, parts, torque specs, safety notes
"""

import sys
import os

_rag = os.path.join(os.path.dirname(__file__), "..", "rag")
if _rag not in sys.path:
    sys.path.insert(0, _rag)

from llm import analyze_root_cause, generate_repair_steps
from state import OrchestratorState


_FALLBACK_DIAGNOSIS = {
    "probable_cause": "Sensor anomaly detected — LLM unavailable (rate limit)",
    "confidence": "Low",
    "reasoning": "Automatic fallback: Gemini API quota exceeded.",
    "recommended_action": "Inspect machine manually.",
}

_FALLBACK_REPAIR = {
    "steps": ["Inspect machine", "Check sensor readings", "Contact maintenance supervisor"],
    "parts_needed": [],
    "torque_specs": [],
    "safety_notes": ["Follow standard safety procedures"],
}


def triage_node(state: OrchestratorState) -> dict:
    print(
        f"\n[TRIAGE] {state['machine_id']} | {state['sensor_type']} "
        f"avg={state['average_value']} | {state['severity']}"
    )

    try:
        diagnosis = analyze_root_cause(
            machine_id=state["machine_id"],
            machine_type=state["machine_type"],
            sensor_type=state["sensor_type"],
            average_value=state["average_value"],
            severity=state["severity"],
        )
        repair_steps = generate_repair_steps(
            machine_type=state["machine_type"],
            fault_type=diagnosis.get("probable_cause", "unknown fault"),
        )
    except Exception as e:
        print(f"[TRIAGE] LLM unavailable ({e.__class__.__name__}) — using fallback diagnosis")
        diagnosis    = _FALLBACK_DIAGNOSIS
        repair_steps = _FALLBACK_REPAIR

    print(f"[TRIAGE] → {diagnosis.get('probable_cause')} ({diagnosis.get('confidence')} confidence)")
    print(f"[TRIAGE] → {len(repair_steps.get('steps', []))} steps, {len(repair_steps.get('parts_needed', []))} parts")

    return {"diagnosis": diagnosis, "repair_steps": repair_steps}
