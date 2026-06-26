import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from .orchestrator import AIOrchestrator

class SystemAgent:
    """
    Autonomous execution agent for Forensic AI OS.
    Capable of planning and executing tasks across forensic services.
    """

    def __init__(self):
        self.orchestrator = AIOrchestrator()
        self.task_log = []

    def execute_instruction(self, instruction: str) -> Dict[str, Any]:
        """
        Main entry point for autonomous execution.
        Analyzes the instruction, creates a plan, and executes it.
        """
        # 1. Use AI to plan the steps (Narrow AI Context)
        plan_prompt = f"""
        Translate the following user instruction into a sequence of system actions for Forensic AI OS.
        Instruction: "{instruction}"
        
        Available Actions:
        - scan_disk(image_path): Triggers the file carver
        - analyze_metadata(evidence_id): Runs metadata extraction
        - generate_report(case_id): Produces a full AI report
        - summarize_findings(text): Summarizes forensic data
        
        Return a JSON list of steps.
        """
        
        # In a real implementation, we'd call the LLM to get the JSON plan.
        # For MVP, we use a rule-based mapper or a mock response if LLM fails.
        
        self.log_action("planning", f"Analyzing instruction: {instruction}")
        
        # Mocking the AI planning response for now
        if "scan" in instruction.lower() or "find" in instruction.lower():
            plan = [
                {"action": "scan_disk", "params": {"image_path": "auto_detect"}},
                {"action": "summarize_findings", "params": {"text": "latest_output"}}
            ]
        else:
            plan = [
                {"action": "summarize_findings", "params": {"text": instruction}}
            ]

        results = []
        for step in plan:
            result = self.dispatch_action(step["action"], step["params"])
            results.append(result)
            self.log_action(step["action"], f"Executed with result: {str(result)[:100]}")

        return {
            "status": "completed",
            "instruction": instruction,
            "plan": plan,
            "results": results,
            "log": self.task_log
        }

    def dispatch_action(self, action: str, params: Dict[str, Any]) -> Any:
        """Route actions to the appropriate system service."""
        # This would import services from other modules
        # For MVP, we provide descriptive success messages or call placeholders
        if action == "scan_disk":
            from forensic_engine.file_carver import FileCarver
            carver = FileCarver()
            return {"status": "success", "message": "Disk carving initiated across all known signatures."}
        
        elif action == "summarize_findings":
            return {"summary": self.orchestrator.summarize(params.get("text", ""))}
        
        return {"status": "unsupported", "action": action}

    def log_action(self, action: str, details: str):
        self.task_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details
        })
