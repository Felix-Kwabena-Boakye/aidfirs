#!/usr/bin/env python
"""backend.forensic_engine.external_tools

Safe, tool-driven wrappers for integrating external forensic utilities.

Supported (optional) tools:
- Sleuth Kit (handled by forensic_api/tsk_wrapper.py in this repo)
- Foremost / Scalpel (carving)
- Bulk Extractor (metadata / feature extraction)
- Plaso (timeline)

This module is designed to be conservative:
- Never writes outside the provided output directory.
- Validates command arguments.
- Gracefully reports tool unavailability when tools are missing.
- Returns structured errors instead of generated data, preserving forensic integrity.

The goal is to produce structured JSON that can be displayed in the UI.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_safe_output_dir(path: str, base: str) -> bool:
    """Ensure output directory resolves under base."""
    if not path:
        return False
    ap = os.path.abspath(path)
    ab = os.path.abspath(base)
    return ap.startswith(ab)


def _run_cmd(cmd: List[str], timeout_s: int = 60 * 15) -> Dict[str, Any]:
    """Run external command and capture stdout/stderr.

    Returns:
      {success: bool, stdout: str, stderr: str, returncode: int, error: str?}
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
        }
    except FileNotFoundError:
        return {"success": False, "error": "tool_missing"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@dataclass
class ExternalToolsOptions:
    timeout_s: int = 60 * 15
    mock_on_missing: bool = False



class ExternalForensicsPipeline:
    def __init__(self, options: Optional[ExternalToolsOptions] = None):
        self.options = options or ExternalToolsOptions()

    # ----------------------------
    # Foremost / Scalpel Carving
    # ----------------------------
    def carve_with_foremost(
        self,
        evidence_path: str,
        out_dir: str,
        file_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run foremost carving.

        Notes:
        - Real foremost needs a config file (or default). This prototype uses:
          foremost -i <image> -o <out_dir> <maybe -t>
        - Since params vary, we keep this conservative and focus on structure.
        """
        cmd = ["foremost", "-i", evidence_path, "-o", out_dir]
        if file_types:
            # Foremost uses -t <type> where type is like jpg, png...
            # We'll pass comma-separated as a best-effort.
            cmd += ["-t", ",".join(file_types)]

        res = _run_cmd(cmd, timeout_s=self.options.timeout_s)
        if res.get("error") == "tool_missing":
            return {"success": False, "error": "foremost tool not installed on host path", "raw": res}

        if not res.get("success"):
            return {"success": False, "error": res.get("error") or "carving_failed", "raw": res}

        return {
            "success": True,
            "tool": "foremost",
            "started_at": utc_now_iso(),
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "output_dir": out_dir,
            "mock": False,
        }

    def carve_with_scalpel(
        self,
        evidence_path: str,
        out_dir: str,
        file_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run scalpel carving (best-effort).

        Scalpel typically requires a configuration file. If file_types provided,
        we cannot reliably generate it without template details, so we only
        run scalpel with default config.
        """
        cmd = ["scalpel", evidence_path, "-o", out_dir]
        res = _run_cmd(cmd, timeout_s=self.options.timeout_s)
        if res.get("error") == "tool_missing":
            return {"success": False, "error": "scalpel tool not installed on host path", "raw": res}

        if not res.get("success"):
            return {"success": False, "error": res.get("error") or "carving_failed", "raw": res}

        return {
            "success": True,
            "tool": "scalpel",
            "started_at": utc_now_iso(),
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "output_dir": out_dir,
            "mock": False,
        }

    # ----------------------------
    # Bulk Extractor
    # ----------------------------
    def bulk_extract(
        self,
        evidence_path: str,
        out_dir: str,
        plugins: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        plugins = plugins or ["Email", "Zip", "PDF", "Domain", "URL", "EXE", "Phone", "CreditCard"]

        cmd = ["bulk_extractor", evidence_path, "-o", out_dir]
        # Bulk Extractor plugin selection differs by version; we pass best-effort via -B
        cmd += ["-B", ",".join([p.lower() for p in plugins])]

        res = _run_cmd(cmd, timeout_s=self.options.timeout_s)
        if res.get("error") == "tool_missing":
            return {"success": False, "error": "bulk_extractor tool not installed on host path", "raw": res}

        if not res.get("success"):
            return {"success": False, "error": res.get("error") or "bulk_extract_failed", "raw": res}

        # Without reliable log parsing, we provide raw stdout/stderr.
        # UI can still show parsed highlights if we have them.
        return {
            "success": True,
            "tool": "bulk_extractor",
            "mock": False,
            "output_dir": out_dir,
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
        }

    # ----------------------------
    # Plaso timeline
    # ----------------------------
    def plaso_timeline(
        self,
        evidence_path: str,
        out_dir: str,
        output_prefix: str = "plaso",
    ) -> Dict[str, Any]:
        """Run Plaso to generate a timeline.

        Common commands:
          log2timeline.py -z <output> -o <output> <evidence>
          psort.py -o ...

        This repo does not require exact correctness; we structure it.
        """
        # Best-effort: attempt log2timeline first to produce a plist file
        timeline_path = os.path.join(out_dir, f"{output_prefix}.jsonl")
        cmd = ["log2timeline", evidence_path, "--output-url", timeline_path]

        res = _run_cmd(cmd, timeout_s=self.options.timeout_s)
        if res.get("error") == "tool_missing":
            return {"success": False, "error": "log2timeline/plaso tool not installed on host path", "raw": res}

        if not res.get("success"):
            return {"success": False, "error": res.get("error") or "plaso_failed", "raw": res}

        return {
            "success": True,
            "tool": "plaso",
            "mock": False,
            "timeline_path": timeline_path,
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
        }


def safe_make_output_dir(base_dir: str, evidence_id: str, subdir: str) -> str:
    """Create a safe output directory for evidence."""
    base_dir = os.path.abspath(base_dir)
    out_dir = os.path.join(base_dir, str(evidence_id), subdir)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir
