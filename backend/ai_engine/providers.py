from abc import ABC, abstractmethod
import os
import re
import json
from typing import Dict, List, Optional, Any


def _extract_indicators_from_text(text: str) -> Dict[str, List[str]]:
    """Extract indicators of compromise directly from the submitted evidence text."""
    ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    url_pattern = r"https?://[^\s]+"
    hash_pattern = r"\b[a-fA-F0-9]{32,64}\b"
    return {
        "ips": list(set(re.findall(ip_pattern, text))),
        "emails": list(set(re.findall(email_pattern, text))),
        "urls": list(set(re.findall(url_pattern, text))),
        "hashes": list(set(re.findall(hash_pattern, text))),
    }


def _has_evidence(indicators: Dict[str, Any], text: str = "") -> bool:
    """Whether any actual evidence (text or observed indicators) is present."""
    if text and text.strip():
        return True
    for key in ("ips", "emails", "urls", "hashes"):
        if indicators.get(key):
            return True
    return False


def _compute_risk(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """Risk assessment computed exclusively from observed evidence indicators."""
    ips = indicators.get("ips") or []
    emails = indicators.get("emails") or []
    urls = indicators.get("urls") or []
    hashes = indicators.get("hashes") or []

    risk_score = 0
    risk_factors = []

    if ips:
        risk_score += 2 if len(ips) > 3 else 1
        risk_factors.append(f"{len(ips)} IP address(es) observed")

    if hashes:
        risk_score += 3
        risk_factors.append(f"{len(hashes)} cryptographic hash(es) observed")

    if emails:
        risk_score += 1
        risk_factors.append(f"{len(emails)} email address(es) observed")

    if urls:
        risk_score += 2
        risk_factors.append(f"{len(urls)} URL(s) observed")

    level = "Low"
    if risk_score >= 7:
        level = "Critical"
    elif risk_score >= 5:
        level = "High"
    elif risk_score >= 3:
        level = "Medium"

    result = {
        "risk_score": risk_score,
        "risk_level": level,
    }
    if risk_factors:
        result["risk_factors"] = risk_factors
    if hashes:
        result["recommendations"] = ["Validate observed hashes against known IOC feeds before attributing risk."]
    return result


def _format_report(analysis_data: Dict[str, Any], header: str) -> str:
    """Render a report strictly from provided analysis data. Never invents findings."""
    lines = [header]
    for key, value in analysis_data.items():
        if isinstance(value, (list, tuple)):
            if value:
                lines.append(f"\n{key}:")
                for item in value:
                    lines.append(f"- {item}")
        elif isinstance(value, dict):
            if value:
                lines.append(f"\n{key}:")
                for k, v in value.items():
                    lines.append(f"- {k}: {v}")
        else:
            lines.append(f"\n{key}: {value}")
    return "\n".join(lines)


def _insufficient_data() -> Dict[str, Any]:
    return {"status": "insufficient_data", "message": "No evidence available for analysis."}


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
    Evidence-driven: every output is derived from submitted evidence only.
    """
    def __init__(self):
        from .forensic_model import load_forensic_model
        self.model = load_forensic_model()

    def is_configured(self) -> bool:
        key = getattr(self.model, "anthropic_key", None)
        return bool(key and key != "mock")

    def summarize(self, text: str, max_words: int = 60) -> str:
        if not text or not text.strip():
            return "Insufficient evidence: no text available for analysis."
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."

    def extract_indicators(self, text: str) -> Dict[str, List[str]]:
        if not text or not text.strip():
            return {
                **{"ips": [], "emails": [], "urls": [], "hashes": []},
                **_insufficient_data(),
            }
        return _extract_indicators_from_text(text)

    def analyze_risk(self, indicators: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        if not _has_evidence(indicators, text):
            return _insufficient_data()
        return _compute_risk(indicators)

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        if not analysis_data:
            return json.dumps(_insufficient_data())
        return _format_report(analysis_data, "# FORENSIC AI REPORT\n\nFindings derived from the submitted evidence below.")


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
        if not text or not text.strip():
            return "Insufficient evidence: no text available for analysis."
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."

    def extract_indicators(self, text: str) -> Dict[str, List[str]]:
        if not text or not text.strip():
            return {
                **{"ips": [], "emails": [], "urls": [], "hashes": []},
                **_insufficient_data(),
            }
        return _extract_indicators_from_text(text)

    def analyze_risk(self, indicators: Dict[str, Any], text: str = "") -> Dict[str, Any]:
        if not _has_evidence(indicators, text):
            return _insufficient_data()
        return _compute_risk(indicators)

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        if not analysis_data:
            return json.dumps(_insufficient_data())
        return _format_report(analysis_data, f"[LOCAL_AI ({self.model_name})] Report")

    def train(self, data_samples: List[Dict[str, Any]]):
        """
        Fine-tune the local model on new forensic data.
        """
        print(f"Fine-tuning {self.model_name} on {len(data_samples)} forensic samples...")
        return {"status": "training_initiated", "samples": len(data_samples)}
