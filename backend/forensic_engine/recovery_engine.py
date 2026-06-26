#!/usr/bin/env python
"""backend.forensic_engine.recovery_engine

Orchestrates forensic-sound file recovery from disk images / raw media.

This module is intentionally conservative:
- It never modifies the input evidence.
- It produces a structured report and (optionally) carved output files.
- It hashes carved output (MD5 + SHA-256) and includes scan parameters.

Note: The current repository's filesystem parsing is heuristic/simulated.
This engine focuses on reproducible scanning + carving based on headers/footers.
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from .file_carver import FileCarver
from .metadata_recovery import DiskImageAnalyzer


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def md5_sha256_for_file(path: str) -> Dict[str, str]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return {"md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


@dataclass
class RecoveryOptions:
    file_types: Optional[List[str]] = None
    scan_chunk_size: int = 8192
    carve: bool = False
    out_dir: Optional[str] = None
    max_carved_per_type: int = 200
    max_carve_bytes: int = 2 * 1024 * 1024 * 1024  # 2GB safety cap for carving

    # External-tool pipeline (best-effort + mock fallback)
    use_foremost: bool = False
    use_scalpel: bool = False
    use_bulk_extractor: bool = False
    use_plaso: bool = False
    bulk_plugins: Optional[List[str]] = None





class RecoveryEngine:

    def __init__(self, options: Optional[RecoveryOptions] = None):
        self.options = options or RecoveryOptions()

    def recover(self, image_path: str, filesystem_type: str = "ntfs") -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "image_path": image_path,
            "filesystem_type": filesystem_type,
            "recovery_time": utc_now_iso(),
            "scan": {
                "file_types": self.options.file_types,
                "scan_chunk_size": self.options.scan_chunk_size,
                "carve": self.options.carve,
                "out_dir": self.options.out_dir,
                "max_carved_per_type": self.options.max_carved_per_type,
                "max_carve_bytes": self.options.max_carve_bytes,
            },
            "evidence_hashes": {},
            "carved_files": [],
            "timestamps": [],
            "filesystem_metadata": [],
            "statistics": {},
            "errors": [],
            "external_tools": {
                "foremost": None,
                "scalpel": None,
                "bulk_extractor": None,
                "plaso": None,
            },
        }


        # Evidence hashes (read-only)
        if os.path.exists(image_path):
            try:
                st = os.stat(image_path)
                out["evidence_size"] = st.st_size
                out["evidence_hashes"] = md5_sha256_for_file(image_path)
            except Exception as e:
                out["errors"].append({"stage": "evidence_hash", "error": str(e)})

        # Filesystem-ish metadata + timestamp heuristics
        try:
            analyzer = DiskImageAnalyzer()
            meta = analyzer.full_analysis(image_path, filesystem_type=filesystem_type)
            out["timestamps"] = meta.get("timestamps", [])
            out["filesystem_metadata"] = meta.get("recovered_files", [])
        except Exception as e:
            out["errors"].append({"stage": "filesystem_metadata", "error": str(e)})

        # Carving (headers/footers) - internal signature scan (fast, always on)
        try:
            carver = FileCarver(chunk_size=self.options.scan_chunk_size)
            carved_meta = carver.carve_disk_image(image_path, file_types=self.options.file_types)

            # Optionally extract bytes for carved candidates

            carved_files: List[Dict[str, Any]] = []
            if self.options.carve:
                if not self.options.out_dir:
                    raise ValueError("out_dir must be provided when carve=True")
                os.makedirs(self.options.out_dir, exist_ok=True)
                carved_files = carver.extract_carved_bytes(
                    image_path=image_path,
                    carved_candidates=carved_meta,
                    out_dir=self.options.out_dir,
                    max_carved_per_type=self.options.max_carved_per_type,
                    max_total_bytes=self.options.max_carve_bytes,
                )
            else:
                carved_files = [
                    {
                        "file_type": c.get("file_type"),
                        "offset": c.get("offset"),
                        "estimated_size": c.get("estimated_size"),
                        "header_signature": c.get("header_signature"),
                        "footer_found": c.get("footer_found"),
                        "recovery_confidence": c.get("recovery_confidence"),
                        "timestamp": c.get("timestamp"),
                    }
                    for c in carved_meta
                ]

            out["carved_files"] = carved_files
        except Exception as e:
            out["errors"].append({"stage": "carving", "error": str(e)})

        # External tools (optional)
        try:
            from .external_tools import ExternalForensicsPipeline, ExternalToolsOptions, safe_make_output_dir

            from .bulk_extractor_parser import parse_bulk_extractor_summary
            from .plaso_parser import parse_plaso_timeline_jsonl

            out_base = None
            # If caller provided out_dir, reuse; else create a safe storage subdir under storage/recoveries/<evidence_hash>/
            if self.options.out_dir:
                out_base = self.options.out_dir
            else:
                # Best-effort: use evidence file name as directory key (sanitized basename)
                ev_key = os.path.basename(image_path) or "evidence"
                safe_root = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage")), "recoveries")
                out_base = safe_make_output_dir(safe_root, ev_key, "external")

            pipeline = ExternalForensicsPipeline(options=ExternalToolsOptions())

            external_tools_out: Dict[str, Any] = out.get("external_tools") or {}

            if self.options.use_foremost or self.options.use_scalpel:
                carved_dir = os.path.join(out_base, "carving")
                os.makedirs(carved_dir, exist_ok=True)
                if self.options.use_foremost:
                    foremost_res = pipeline.carve_with_foremost(image_path=image_path, out_dir=carved_dir, file_types=self.options.file_types)
                    external_tools_out["foremost"] = foremost_res
                if self.options.use_scalpel:
                    scalpel_res = pipeline.carve_with_scalpel(image_path=image_path, out_dir=carved_dir, file_types=self.options.file_types)
                    external_tools_out["scalpel"] = scalpel_res

            if self.options.use_bulk_extractor:
                be_dir = os.path.join(out_base, "bulk_extractor")
                os.makedirs(be_dir, exist_ok=True)
                be_res = pipeline.bulk_extract(evidence_path=image_path, out_dir=be_dir, plugins=self.options.bulk_plugins)
                be_summary = parse_bulk_extractor_summary(be_dir, raw_stdout=be_res.get("stdout", "") if isinstance(be_res, dict) else "")
                be_res["parsed"] = be_summary
                external_tools_out["bulk_extractor"] = be_res

            if self.options.use_plaso:
                plaso_dir = os.path.join(out_base, "plaso")
                os.makedirs(plaso_dir, exist_ok=True)
                pl_res = pipeline.plaso_timeline(evidence_path=image_path, out_dir=plaso_dir, output_prefix="timeline")
                if pl_res.get("success") and pl_res.get("timeline_path"):
                    pl_parsed = parse_plaso_timeline_jsonl(pl_res["timeline_path"], top_n=200)
                    pl_res["parsed"] = pl_parsed
                external_tools_out["plaso"] = pl_res

            out["external_tools"] = external_tools_out
        except Exception as e:
            out.setdefault("external_tools", {})
            out["external_tools"]["error"] = str(e)

        # Stats
        types: Dict[str, int] = {}
        for item in out.get("carved_files", []):
            t = item.get("file_type", "unknown")
            types[t] = types.get(t, 0) + 1
        out["statistics"] = {
            "carved_count": len(out.get("carved_files", [])),
            "carved_by_type": types,
            "timestamp_count": len(out.get("timestamps", [])),
        }

        return out


    def recover_to_report(self, image_path: str, filesystem_type: str = "ntfs", report_path: Optional[str] = None) -> Dict[str, Any]:
        report = self.recover(image_path=image_path, filesystem_type=filesystem_type)
        if report_path:
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        return report

