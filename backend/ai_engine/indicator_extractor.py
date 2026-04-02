import re
from .claude_client import ClaudeClient


class IndicatorExtractor:

    def __init__(self):
        self.claude = ClaudeClient()

    def extract(self, text: str):
        """
        Extract indicators of compromise from text using regex and Claude AI.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing extracted indicators
        """
        # Basic regex-based extraction
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        url_pattern = r"https?://[^\s]+"
        hash_pattern = r"\b[a-fA-F0-9]{32,64}\b"

        indicators = {
            "ips": list(set(re.findall(ip_pattern, text))),
            "emails": list(set(re.findall(email_pattern, text))),
            "urls": list(set(re.findall(url_pattern, text))),
            "hashes": list(set(re.findall(hash_pattern, text))),
        }

        # Use Claude for enhanced extraction if configured
        if self.claude.is_configured():
            try:
                enhanced = self.claude.extract_indicators(text)
                # Merge enhanced indicators with regex-based ones
                for key, value in enhanced.items():
                    if key in indicators:
                        indicators[key] = list(set(indicators[key] + value))
                    elif value:
                        indicators[key] = value
            except Exception as e:
                print(f"Claude indicator extraction failed: {e}")

        return indicators
