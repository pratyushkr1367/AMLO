"""
Technician Assignment Engine — picks the best available technician for a repair.

Scoring per technician:
  skill_match × proximity_score

skill_match  : 1.5 if the technician has the required skill, 1.0 otherwise
proximity    : 1 / (1 + manhattan_distance) — higher when closer to the machine
"""

import httpx

LOGISTICS_URL = "http://localhost:8005"

# Maps machine type to the skill tag used in the technicians table
SKILL_MAP: dict[str, str] = {
    "CNC":    "CNC",
    "Lathe":  "Lathe",
    "Press":  "hydraulics",
    "Welder": "Welder",
}


def assign(
    machine_type: str,
    machine_row: int,
    machine_col: int,
) -> dict | None:
    """
    Returns the highest-scoring available technician dict, or None if no one is available.
    """
    required_skill = SKILL_MAP.get(machine_type, machine_type)

    # Try skill-filtered first, fall back to all available
    technicians = _fetch_available(skill=required_skill)
    if not technicians:
        technicians = _fetch_available()
    if not technicians:
        return None

    def score(tech: dict) -> float:
        skill_match = 1.5 if required_skill in tech.get("skills", []) else 1.0
        distance = abs(tech["location_row"] - machine_row) + abs(tech["location_col"] - machine_col)
        proximity = 1.0 / (1.0 + distance)
        return skill_match * proximity

    return max(technicians, key=score)


def _fetch_available(skill: str | None = None) -> list[dict]:
    params = {"skill": skill} if skill else {}
    try:
        response = httpx.get(f"{LOGISTICS_URL}/technicians/available", params=params, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []
