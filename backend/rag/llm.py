"""
LLM Integration — Phase 6, AMLO

Supports two providers switchable at runtime:
  - "gemini" : Google Gemini via google-genai SDK
  - "local"  : Ollama (gemma3:4b or any pulled model) via HTTP

Three functions:
  analyze_root_cause()    — probable fault + confidence from anomaly + manual context
  generate_repair_steps() — step-by-step repair instructions with torque specs
  draft_work_order()      — structured JSON work order ready for the Work Order Service
"""

import json
import time
import httpx
from google import genai
from google.genai import errors as genai_errors

from config import GEMINI_API_KEY, LLM_MODEL, LLM_PROVIDER, LOCAL_LLM_URL, LOCAL_LLM_MODEL
from search import search, format_context

client = genai.Client(api_key=GEMINI_API_KEY)

_provider = LLM_PROVIDER  # mutable at runtime


def get_provider() -> str:
    return _provider


def set_provider(provider: str):
    global _provider
    if provider not in ("gemini", "local"):
        raise ValueError(f"Unknown provider '{provider}' — use 'gemini' or 'local'")
    _provider = provider
    print(f"[LLM] Provider switched to: {provider}")


def _call_gemini(prompt: str, retries: int = 2) -> str:
    for attempt in range(retries):
        try:
            return client.models.generate_content(model=LLM_MODEL, contents=prompt).text.strip()
        except genai_errors.ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 35 * (attempt + 1)
                print(f"[LLM] Gemini rate limited — waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Gemini rate limit exceeded after retries")


def _call_local(prompt: str) -> str:
    response = httpx.post(
        f"{LOCAL_LLM_URL}/api/generate",
        json={"model": LOCAL_LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _call(prompt: str) -> str:
    if _provider == "local":
        return _call_local(prompt)
    return _call_gemini(prompt)


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM output, stripping markdown code fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)


# ─── 1. Root Cause Analysis ───────────────────────────────────────────────────
def analyze_root_cause(
    machine_id: str,
    machine_type: str,
    sensor_type: str,
    average_value: float,
    severity: str,
) -> dict:
    query = f"{machine_type} machine {sensor_type} anomaly fault diagnosis {severity}"
    chunks = search(query)
    context = format_context(chunks)

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


# ─── 2. Repair Instructions ───────────────────────────────────────────────────
def generate_repair_steps(machine_type: str, fault_type: str) -> dict:
    query = f"{machine_type} {fault_type} repair procedure steps torque specifications parts"
    chunks = search(query)
    context = format_context(chunks)

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


# ─── 3. Work Order Drafting ───────────────────────────────────────────────────
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
