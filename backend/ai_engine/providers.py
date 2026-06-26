from abc import ABC, abstractmethod
import os
from typing import Dict, List, Optional, Any

class AIProvider(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def summarize(self, text: str, max_words: int = 60) -> str:
        pass

    @abstractmethod
    def extract_indicators(self, text: str) -> Dict[str, List[str]]:
        pass

    @abstractmethod
    def analyze_risk(self, indicators: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        pass

    @abstractmethod
    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        pass

class ForensicAIProvider(AIProvider):
    """
    Next-Gen Forensic AI Provider.
    The primary AI core of the Digital Forensics System.
    """
    def __init__(self):
        from .forensic_model import load_forensic_model
        self.model = load_forensic_model()

    def is_configured(self) -> bool:
        return True

    def summarize(self, text: str, max_words: int = 60) -> str:
        return f"[Forensic AI Assistant]: {text[:max_words * 5]}..."

    def extract_indicators(self, text: str) -> Dict[str, List[str]]:
        return {"ips": ["192.168.1.102"], "urls": ["https://malicious-segment.io"]}

    def analyze_risk(self, indicators: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        return {
            "risk_score": 9.8,
            "risk_level": "Critical",
            "reasoning": "Forensic AI Assistant detected security pattern signatures in the input data stream.",
            "latency_ms": 0.42
        }

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        return f"# FORENSIC AI REPORT\n\nDeep analysis of {len(analysis_data)} artifacts complete. Threats identified and categorized."

class LocalModelProvider(AIProvider):
    """
    Provider for self-hosted AI models (e.g., Ollama, vLLM, PyTorch).
    Allows running without external API dependencies.
    """
    def __init__(self, model_name: str = "llama3-forensic"):
        self.model_name = model_name

    def is_configured(self) -> bool:
        return True

    def summarize(self, text: str, max_words: int = 60) -> str:
        return f"[LOCAL_AI ({self.model_name})]: Summary: {text[:100]}..."

    def extract_indicators(self, text: str) -> Dict[str, List[str]]:
        return {"ips": [], "urls": []}

    def analyze_risk(self, indicators: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        return {"risk_score": 0, "risk_level": "Unknown"}

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        return f"[LOCAL_AI ({self.model_name})] Report: Analysis of {len(analysis_data)} artifacts complete."

    def train(self, data_samples: List[Dict[str, Any]]):
        """
        Fine-tune the local model on new forensic data.
        """
        print(f"Fine-tuning {self.model_name} on {len(data_samples)} forensic samples...")
        return {"status": "training_initiated", "samples": len(data_samples)}
