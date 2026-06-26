o#!/usr/bin/env python
"""backend.forensic_engine.bulk_extractor_parser

Lightweight normalization of Bulk Extractor outputs.

This repository currently runs Bulk Extractor best-effort and may only obtain
stdout/stderr in many environments. This parser therefore supports:
- If an output directory contains typical BE result files, summarize them.
- Otherwise, fall back to parsing stdout for common patterns.

The implementation is intentionally heuristic.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List


EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s\"'>)]+", re.IGNORECASE)


def parse_bulk_extractor_summary(output_dir: str, raw_stdout: str = "") -> Dict[str, Any]:
    highlights: List[Dict[str, Any]] = []

    if output_dir and os.path.isdir(output_dir):
        # Best-effort search for common BE output filenames
        for fn in os.listdir(output_dir):
            lower = fn.lower()
            path = os.path.join(output_dir, fn)
            try:
                if not os.path.isfile(path):
                    continue
                content = open(path, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue

            if "email" in lower or "email" in content[:2000].lower():
                for m in EMAIL_RE.findall(content)[:50]:
                    highlights.append({"type": "email", "value": m})

            if "url" in lower or "http" in content[:2000].lower():
                for m in URL_RE.findall(content)[:50]:
                    highlights.append({"type": "url", "value": m})

    # Fallback to raw stdout
    if not highlights and raw_stdout:
        for m in EMAIL_RE.findall(raw_stdout)[:20]:
            highlights.append({"type": "email", "value": m})
        for m in URL_RE.findall(raw_stdout)[:20]:
            highlights.append({"type": "url", "value": m})

    return {
        "highlights": highlights,
        "summary": {
            "highlight_count": len(highlights),
        },
    }

