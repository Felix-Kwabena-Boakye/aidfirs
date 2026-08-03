import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from .orchestrator import AIOrchestrator

class SystemAgent:
    """
    Autonomous execution agent for Forensic AI OS.
    Executes tasks against real forensic services and reports actual outcomes.
    """

    def __init__(self):
        self.orchestrator = AIOrchestrator()
        self.task_log = []

    def execute_instruction(self, instruction: str) -> Dict[str, Any]:
        """
        Main entry point for autonomous execution.
        Analyzes the instruction, builds a plan, and executes supported actions.
        """
        self.log_action("planning", f"Analyzing instruction: {instruction}")

        plan = self._plan(instruction)

        results = []
        for step in plan:
            result = self.dispatch_action(step["action"], step["params"])
            results.append(result)
            self.log_action(step["action"], f"Result: {str(result)[:200]}")

        statuses = {r.get("status") for r in results}
        if statuses and statuses.issubset({"no_task"}):
            status = "no_task"
        else:
            status = "completed"

        return {
            "status": status,
            "instruction": instruction,
            "plan": plan,
            "results": results,
            "log": self.task_log
        }

    def _plan(self, instruction: str) -> List[Dict[str, Any]]:
        """Rule-based plan proposal. Only genuinely executable actions are included."""
        lowered = instruction.lower()
        if any(word in lowered for word in ("scan", "carve", "recover", "find", "analyze")):
            image_path = self._extract_image_path(instruction)
            return [
                {"action": "scan_disk", "params": {"image_path": image_path}},
            ]
        return [
            {"action": "unsupported", "params": {"instruction": instruction}},
        ]

    def _extract_image_path(self, instruction: str) -> str:
        """Best-effort extraction of a disk image path from the instruction text."""
        patterns = [
            r"([A-Za-z]:\\(?:[^\"'\\]+\\)*[^\"'\\]+\.(?:raw|img|e01|dd))",
            r"(/\S+\.(?:raw|img|e01|dd))",
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def dispatch_action(self, action: str, params: Dict[str, Any]) -> Any:
        """Route actions to the appropriate system service and report the real outcome."""
        if action == "scan_disk":
            return self._scan_disk(params)

        elif action == "summarize_findings":
            text = params.get("text", "")
            if not text or not text.strip():
                return {
                    "status": "no_task",
                    "message": "No autonomous forensic task currently running. No text was provided to summarize.",
                }
            return {"status": "success", "summary": self.orchestrator.summarize(text)}

        elif action == "generate_report":
            return {
                "status": "no_task",
                "message": "No autonomous forensic task currently running. Report generation requires a case context; use the report endpoint.",
            }

        return {
            "status": "no_task",
            "message": "No autonomous forensic task currently running.",
        }

    def _scan_disk(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a real signature scan only when a real image path is available."""
        image_path = params.get("image_path") or params.get("path") or ""
        if not image_path or image_path == "auto_detect":
            return {
                "status": "no_task",
                "message": "No autonomous forensic task currently running. No disk image path was provided to scan.",
            }
        if not os.path.exists(image_path):
            return {
                "status": "no_task",
                "message": f"No autonomous forensic task currently running. Image path does not exist: {image_path}",
            }

        from forensic_engine.file_carver import FileCarver
        carver = FileCarver()
        carved_metadata = carver.carve_disk_image(image_path)
        return {
            "status": "success",
            "message": f"Disk signature scan completed on {os.path.basename(image_path)}.",
            "signatures_found": len(carved_metadata),
        }

    def log_action(self, action: str, details: str):
        self.task_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details
        })
