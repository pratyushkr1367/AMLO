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

from root_cause_analyzer import analyze_root_cause
from repair_advisor import generate_repair_steps
from state import OrchestratorState

# Cache keyed by (machine_type, sensor_type, severity) — only stores successful LLM results
_triage_cache: dict[tuple, dict] = {}

FALLBACK_FAULT = "Sensor anomaly detected — LLM unavailable (rate limit)"

_FALLBACK_DIAGNOSIS = {
    "probable_cause": FALLBACK_FAULT,
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


def is_fallback(result: dict) -> bool:
    return result.get("diagnosis", {}).get("probable_cause") == FALLBACK_FAULT


def run_triage(machine_type: str, sensor_type: str, severity: str,
               machine_id: str = "", average_value: float = 0.0) -> dict:
    """Run LLM triage and cache on success. Returns result dict."""
    diagnosis = analyze_root_cause(
        machine_id=machine_id,
        machine_type=machine_type,
        sensor_type=sensor_type,
        average_value=average_value,
        severity=severity,
    )
    repair_steps = generate_repair_steps(
        machine_type=machine_type,
        fault_type=diagnosis.get("probable_cause", "unknown fault"),
    )
    result = {"diagnosis": diagnosis, "repair_steps": repair_steps}
    _triage_cache[(machine_type, sensor_type, severity)] = result
    return result


def triage_node(state: OrchestratorState) -> dict:
    print(
        f"\n[TRIAGE] {state['machine_id']} | {state['sensor_type']} "
        f"avg={state['average_value']} | {state['severity']}"
    )

    cache_key = (state["machine_type"], state["sensor_type"], state["severity"])
    if cache_key in _triage_cache:
        print(f"[TRIAGE] Cache hit ({'/'.join(cache_key)}) — skipping LLM")
        return _triage_cache[cache_key]

    try:
        result = run_triage(
            machine_type=state["machine_type"],
            sensor_type=state["sensor_type"],
            severity=state["severity"],
            machine_id=state["machine_id"],
            average_value=state["average_value"],
        )
    except Exception as e:
        print(f"[TRIAGE] LLM unavailable ({e.__class__.__name__}) — using fallback")
        result = {"diagnosis": _FALLBACK_DIAGNOSIS, "repair_steps": _FALLBACK_REPAIR}
        # Do NOT cache fallback — next occurrence will retry the LLM

    diagnosis    = result["diagnosis"]
    repair_steps = result["repair_steps"]
    print(f"[TRIAGE] → {diagnosis.get('probable_cause')} ({diagnosis.get('confidence')} confidence)")
    print(f"[TRIAGE] → {len(repair_steps.get('steps', []))} steps, {len(repair_steps.get('parts_needed', []))} parts")

    return result
