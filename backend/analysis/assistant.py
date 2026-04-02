import os
import anthropic
from django.conf import settings

class ForensicAIAssistant:
    def __init__(self):
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY'))
        self.model = getattr(settings, 'CLAUDE_MODEL', os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307'))
        self.enabled = getattr(settings, 'CLAUDE_ENABLED', True)
        
        if self.enabled and self.api_key:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            self.client = None
            
    def chat(self, case_context, forensic_data, user_message, history=None):
        """
        Send a message to Claude with forensic context and optional history.
        """
        if self.api_key and 'mock' in self.api_key.lower():
            history_info = f" (History: {len(history)} messages)" if history else ""
            return {
                "success": True, 
                "response": f"I am the Forensic AI Assistant (Mock Mode). You asked: '{user_message}'{history_info}. In a real environment, I would analyze the partition data and file system structures to help you identify suspicious activity."
            }

        if not self.client:
            return {"success": False, "error": "AI Assistant is not configured or enabled."}
            
        system_prompt = f"""You are an expert digital forensics AI assistant helping an investigator.
Your job is to analyze data extracted from disk images (like partition tables, file lists, or timelines) and answer the investigator's questions.

CASE CONTEXT:
{case_context}

LATEST FORENSIC TOOL OUTPUT:
{forensic_data}

Provide clear, professional, and actionable advice. If the forensic data shows suspicious files (like hidden directories, known malware extensions, or deleted files in unusual places), point them out.
"""

        # Prepare messages including history
        messages = []
        if history and isinstance(history, list):
            for msg in history:
                messages.append({"role": msg.get('role'), "content": msg.get('content')})
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages
            )
            
            return {
                "success": True, 
                "response": response.content[0].text
            }
            
        except Exception as e:
            return {"success": False, "error": f"AI Assistant Error: {str(e)}"}

    def classify_files(self, forensic_data):
        """
        Classify files as suspicious, malicious, or benign based on forensic data.
        """
        if not self.client and not (self.api_key and 'mock' in self.api_key.lower()):
            return {"success": False, "error": "AI Assistant is not configured."}

        system_prompt = "You are a forensic expert. Classify the files in the provided data. Output a JSON list of objects with 'name', 'classification' (Suspicious/Benign/Malicious), and 'reason'."
        
        if self.api_key and 'mock' in self.api_key.lower():
            return {
                "success": True,
                "classification": [
                    {"name": "hidden_script.sh", "classification": "Suspicious", "reason": "Hidden file in user directory"},
                    {"name": "system_config.cfg", "classification": "Benign", "reason": "Standard configuration file"}
                ]
            }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Forensic Data:\n{forensic_data}"}]
            )
            return {"success": True, "response": response.content[0].text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def detect_anomalies(self, forensic_data):
        """
        Detect anomalies in file system behavior or metadata.
        """
        if not self.client and not (self.api_key and 'mock' in self.api_key.lower()):
            return {"success": False, "error": "AI Assistant is not configured."}

        system_prompt = "You are a forensic expert. Detect anomalies in the provided data. look for time stomping, unusual file sizes, or unexpected file locations. Output a summary of findings."
        
        if self.api_key and 'mock' in self.api_key.lower():
            return {
                "success": True,
                "anomalies": "Detected potential time-stomping on 3 files. One log file shows a gap of 2 hours during the suspected incident time."
            }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Forensic Data:\n{forensic_data}"}]
            )
            return {"success": True, "response": response.content[0].text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_report(self, case_context, forensic_data, ai_findings):
        """
        Generate a comprehensive forensic report using AI.
        """
        if not self.client and not (self.api_key and 'mock' in self.api_key.lower()):
            return {"success": False, "error": "AI Assistant is not configured."}

        system_prompt = f"""You are a professional forensic analyst. Generate a formal forensic report based on:
CASE INFO: {case_context}
AI FINDINGS: {ai_findings}

The report should be structured with sections for Executive Summary, Evidence Overview, Analysis Methodology, and Detailed Findings."""
        
        if self.api_key and 'mock' in self.api_key.lower():
            return {
                "success": True,
                "report": f"FORENSIC ANALYSIS REPORT\n\nEXECUTIVE SUMMARY: Analysis of evidence for {case_context.splitlines()[0]} revealed several points of interest.\n\nDETAILED FINDINGS:\n1. AI found: {ai_findings[:100]}...\n2. Metadata recovery confirmed deleted files in suspected directories.\n\nCONCLUSION: Evidence supports further investigation into user activities during the suspected window."
            }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Forensic Data Context:\n{forensic_data}"}]
            )
            return {"success": True, "response": response.content[0].text}
        except Exception as e:
            return {"success": False, "error": str(e)}
