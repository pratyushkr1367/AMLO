"""
Repair Advisor — AMLO RAG layer

Queries the vector store for repair procedures then calls the LLM
to generate step-by-step repair instructions with parts and torque specs.
"""

import json
from llm import _call, _parse_json
from search import search, format_context


def generate_repair_steps(machine_type: str, fault_type: str) -> dict:
    query = f"{machine_type} {fault_type} repair procedure steps torque specifications parts"
    context = format_context(search(query))

    prompt = f"""You are a factory maintenance expert writing a repair procedure.

REPAIR TASK:
  Machine Type : {machine_type}
  Fault        : {fault_type}

RELEVANT MANUAL SECTIONS:
{context}

Generate a detailed repair procedure from the manual sections above.
Respond in this exact JSON format:
{{
  "steps": ["step 1", "step 2", "..."],
  "parts_needed": [
    {{"part_number": "PN-XXX-000", "part_name": "Part Name", "quantity": 1}}
  ],
  "torque_specs": ["Bolt X: Y Nm", "..."],
  "safety_notes": ["safety note 1", "..."]
}}
Return only valid JSON, no markdown."""

    raw = _call(prompt)
    try:
        return _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        return {"steps": [raw], "parts_needed": [], "torque_specs": [], "safety_notes": []}
