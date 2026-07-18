from datetime import datetime, timezone
from typing import Dict, List

class TimelineGenerator:
    """Generates timeline events for recovered evidence."""
    @staticmethod
    def create_event(case_id: str, timestamp: datetime, event_type: str, description: str, severity: str = "info") -> Dict:
        return {
            "case_id": case_id,
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
            "event_type": event_type,
            "description": description,
            "severity": severity
        }
