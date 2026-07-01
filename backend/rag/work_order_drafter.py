"""
Work Order Drafter — AMLO RAG layer

Calls the LLM to generate a human-readable work order description
summarising the fault, diagnosis, and repair action.
"""

from llm import _call


def draft_work_order(
    machine_id: str,
    machine_type: str,
    fault_type: str,
    diagnosis: dict,
    technician: dict,
    repair: dict,
) -> dict:
    prompt = f"""You are a maintenance coordinator drafting a work order.

INCIDENT SUMMARY:
  Machine ID   : {machine_id}
  Machine Type : {machine_type}
  Fault        : {fault_type}
  Diagnosis    : {diagnosis.get('probable_cause', '')}
  Confidence   : {diagnosis.get('confidence', '')}

ASSIGNED TECHNICIAN:
  Name         : {technician.get('name', '')}
  Skills       : {technician.get('skills', [])}

REPAIR REQUIRED:
  Steps        : {len(repair.get('steps', []))} steps
  Parts needed : {repair.get('parts_needed', [])}

Generate a concise work order description (2-3 sentences) summarising the fault,
diagnosis, and repair action. Return only the plain text description, no JSON."""

    description = _call(prompt)
    return {
        "fault_type":  fault_type,
        "description": description,
        "priority":    "CRITICAL" if diagnosis.get("confidence") == "High" else "HIGH",
        "parts_used":  repair.get("parts_needed", []),
    }
