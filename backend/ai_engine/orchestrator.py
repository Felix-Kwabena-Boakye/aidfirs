from typing import Dict, List, Any
from .providers import AIProvider, ForensicAIProvider

class AIOrchestrator:
    """
    Central orchestration layer for Forensic AI capabilities.
    """

    def __init__(self, mode: str = "forensics"):
        self.mode = mode
        self.providers: Dict[str, AIProvider] = {
            "forensic-ai": ForensicAIProvider()
        }
        self.active_provider_name = "forensic-ai"

    def get_active_provider(self) -> AIProvider:
        return self.providers[self.active_provider_name]

    def summarize(self, text: str, max_words: int = 60) -> str:
        return self.get_active_provider().summarize(text, max_words)

    def extract_indicators(self, text: str) -> Dict[str, List[str]]:
        return self.get_active_provider().extract_indicators(text)

    def analyze_risk(self, indicators: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        return self.get_active_provider().analyze_risk(indicators, text)

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        return self.get_active_provider().generate_report(analysis_data)

    def get_capability_info(self) -> Dict[str, Any]:
        """Returns info about the current AI capabilities."""
        return {
            "os_name": "Forensic AI OS",
            "active_provider": self.active_provider_name,
            "capabilities": ["Narrow AI", "Forensic Analysis"],
            "roadmap": ["General AI Integration", "Self-Aware Modules"],
            "learning_approaches": ["Supervised", "Unsupervised", "Reinforcement"]
        }
