"""
Priority Scoring Engine — ranks simultaneous incidents so agents handle the worst first.

Score = machine_type_weight × severity_score × time_factor

Higher score = higher priority.
"""

from datetime import datetime, timezone

# Revenue / production impact weight per machine type
MACHINE_TYPE_WEIGHTS: dict[str, float] = {
    "CNC":    1.0,
    "Lathe":  0.8,
    "Press":  1.2,   # hydraulic press failure is most costly
    "Welder": 0.7,
}

SEVERITY_SCORES: dict[str, float] = {
    "DEGRADING": 1.0,
    "CRITICAL":  3.0,
}


class PriorityScorer:
    def score(self, incident: dict) -> float:
        """
        incident keys:
          machine_type  : str   e.g. "CNC"
          severity      : str   "DEGRADING" | "CRITICAL"
          detected_at   : str   ISO timestamp when the anomaly was first detected
        """
        type_weight = MACHINE_TYPE_WEIGHTS.get(incident.get("machine_type", "CNC"), 1.0)
        severity    = SEVERITY_SCORES.get(incident.get("severity", "DEGRADING"), 1.0)

        # Time factor: grows by 1 for every hour the incident sits unresolved
        detected_at = incident.get("detected_at")
        if detected_at:
            age_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(detected_at)).total_seconds()
            time_factor = 1.0 + (age_seconds / 3600.0)
        else:
            time_factor = 1.0

        return round(type_weight * severity * time_factor, 4)

    def rank(self, incidents: list[dict]) -> list[dict]:
        """Return incidents sorted highest score first, each annotated with its score."""
        scored = sorted(incidents, key=self.score, reverse=True)
        for incident in scored:
            incident["priority_score"] = self.score(incident)
        return scored
