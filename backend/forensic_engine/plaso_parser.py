#!/usr/bin/env python
"""backend.forensic_engine.plaso_parser

Parse normalized Plaso timeline JSONL created by external_tools.py (mock or real).

If you later switch to real Plaso output formats, extend this parser.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List


def parse_plaso_timeline_jsonl(timeline_path: str, top_n: int = 200) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = []
    if not timeline_path or not os.path.exists(timeline_path):
        return {"events": [], "summary": {"count": 0}}

    try:
        with open(timeline_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if isinstance(ev, dict):
                        events.append(ev)
                        if len(events) >= top_n:
                            break
                except json.JSONDecodeError:
                    continue
    except Exception:
        return {"events": [], "summary": {"count": 0}}

    summary: Dict[str, Any] = {
        "count": len(events),
        "by_event_type": {},
    }
    for ev in events:
        et = ev.get("event_type") or "unknown"
        summary["by_event_type"][et] = summary["by_event_type"].get(et, 0) + 1

    return {"events": events, "summary": summary}

