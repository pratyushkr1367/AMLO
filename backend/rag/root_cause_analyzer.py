"""
Root Cause Analyzer — AMLO RAG layer

Queries the vector store for relevant manual sections then calls the LLM
to produce a structured fault diagnosis.
"""

import json
from llm import _call, _parse_json
from search import search, format_context


def analyze_root_cause(
    machine_id: str,
    machine_type: str,
    sensor_type: str,
    average_value: float,
    severity: str,
) -> dict:
    query = f"{machine_type} machine {sensor_type} anomaly fault diagnosis {severity}"
    context = format_context(search(query))

    prompt = f"""You are a factory maintenance expert analyzing a machine anomaly.

ANOMALY DATA:
  Machine ID   : {machine_id}
  Machine Type : {machine_type}
  Sensor       : {sensor_type}
  Average Value: {average_value}
  Severity     : {severity}

RELEVANT MANUAL SECTIONS:
{context}

Based on the anomaly data and the manual sections above, provide a root cause analysis.
Respond in this exact JSON format:
{{
  "probable_cause": "short description of the most likely fault",
  "confidence": "High | Medium | Low",
  "reasoning": "explanation referencing specific manual sections",
  "recommended_action": "immediate action the technician should take"
}}
Return only valid JSON, no markdown."""

    raw = _call(prompt)
    try:
        return _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        return {"probable_cause": raw, "confidence": "Unknown", "reasoning": "", "recommended_action": ""}
