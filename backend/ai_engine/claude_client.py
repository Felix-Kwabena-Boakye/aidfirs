import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class ClaudeClient:
    """
    Client for interacting with Claude API to enhance AI analysis capabilities.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize Claude client with API key.
        
        Args:
            api_key: Anthropic API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                print("Warning: anthropic package not installed")

    def is_configured(self) -> bool:
        """Check if Claude API is properly configured."""
        return self.api_key is not None and self.api_key != "mock" and self.client is not None

    def summarize(self, text: str, max_words: int = 60) -> str:
        """
        Use Claude to generate a smart summary of the text.
        
        Args:
            text: Input text to summarize
            max_words: Maximum words in summary
            
        Returns:
            Generated summary
        """
        if not self.is_configured():
            # Fallback to simple summarization
            words = text.split()
            summary = " ".join(words[:max_words])
            return summary + ("..." if len(words) > max_words else "")

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": f"Please provide a concise summary of the following digital forensics text in no more than {max_words} words. Focus on key findings, indicators, and actionable insights:\n\n{text[:4000]}"
                    }
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Claude API error: {e}")
            # Fallback to simple summarization
            words = text.split()
            summary = " ".join(words[:max_words])
            return summary + ("..." if len(words) > max_words else "")

    def extract_indicators(self, text: str) -> dict:
        """
        Use Claude to extract indicators of compromise with enhanced context awareness.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing extracted indicators
        """
        # Default regex-based extraction
        import re
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

        if not self.is_configured():
            return indicators

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=800,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze the following digital forensics text and extract any additional indicators of compromise (IOCs) that may not have been caught by pattern matching. Look for:
- Suspicious domain names
- Malware strain names or families
- Attacker TTPs (tactics, techniques, procedures)
- Filenames or paths mentioned
- Registry keys
- Port numbers
- Protocol names
- User accounts
- Any other relevant security indicators

Return ONLY a JSON object with these keys: additional_ips, additional_domains, malware_names, attack_techniques, filenames, registry_keys, ports, protocols, user_accounts, other_indicators. If none found for a category, use empty arrays.

Text to analyze:
{text[:4000]}"""
                    }
                ]
            )
            
            # Parse Claude's response
            response_text = message.content[0].text
            
            # Try to extract JSON from response
            try:
                # Find JSON in response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    additional = json.loads(json_str)
                    
                    # Merge with regex-based extraction
                    if additional.get("additional_ips"):
                        indicators["ips"] = list(set(indicators["ips"] + additional["additional_ips"]))
                    if additional.get("additional_domains"):
                        indicators["urls"] = list(set(indicators["urls"] + additional["additional_domains"]))
                    if additional.get("filenames"):
                        indicators.setdefault("filenames", []).extend(additional["filenames"])
                    if additional.get("malware_names"):
                        indicators.setdefault("malware", []).extend(additional["malware_names"])
                    if additional.get("attack_techniques"):
                        indicators.setdefault("techniques", []).extend(additional["attack_techniques"])
                    if additional.get("registry_keys"):
                        indicators.setdefault("registry_keys", []).extend(additional["registry_keys"])
                    if additional.get("ports"):
                        indicators.setdefault("ports", []).extend(additional["ports"])
                    if additional.get("other_indicators"):
                        indicators.setdefault("other", []).extend(additional["other_indicators"])
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"Failed to parse Claude response: {e}")
                
        except Exception as e:
            print(f"Claude API error during indicator extraction: {e}")

        return indicators

    def analyze_risk(self, indicators: dict, text: str = "") -> dict:
        """
        Use Claude to perform advanced risk assessment.
        
        Args:
            indicators: Extracted indicators
            text: Original text for context
            
        Returns:
            Risk assessment dictionary
        """
        # Default rule-based detection
        risk_score = 0

        if len(indicators.get("ips", [])) > 3:
            risk_score += 2

        if indicators.get("hashes"):
            risk_score += 3

        if indicators.get("emails"):
            risk_score += 1

        if indicators.get("urls"):
            risk_score += 2

        level = "Low"
        if risk_score >= 5:
            level = "High"
        elif risk_score >= 3:
            level = "Medium"

        result = {
            "risk_score": risk_score,
            "risk_level": level,
            "method": "rule-based"
        }

        if not self.is_configured():
            return result

        try:
            # Create context from indicators
            context = f"Indicators found: {json.dumps(indicators)}"
            if text:
                context += f"\n\nText excerpt: {text[:1000]}"
            
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze the following digital forensics indicators and provide a risk assessment. Consider:
- Number and type of indicators
- Severity of potential threats
- Context from the evidence

Return ONLY a JSON object with these keys:
- risk_score (number 0-10)
- risk_level (Low, Medium, High, or Critical)
- risk_factors (array of strings describing key risk factors)
- recommendations (array of strings with actionable recommendations)

{context}"""
                    }
                ]
            )
            
            # Parse Claude's response
            response_text = message.content[0].text
            
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    claude_assessment = json.loads(json_str)
                    
                    # Merge with rule-based assessment
                    result["risk_score"] = max(risk_score, claude_assessment.get("risk_score", risk_score))
                    result["risk_level"] = claude_assessment.get("risk_level", level)
                    result["risk_factors"] = claude_assessment.get("risk_factors", [])
                    result["recommendations"] = claude_assessment.get("recommendations", [])
                    result["method"] = "ai-enhanced"
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"Failed to parse Claude risk assessment: {e}")
                
        except Exception as e:
            print(f"Claude API error during risk analysis: {e}")

        return result

    def generate_report(self, analysis_data: dict) -> str:
        """
        Use Claude to generate a comprehensive forensic report.
         
        Args:
            analysis_data: Dictionary containing analysis results
            
        Returns:
            Generated report text
        """
        if not self.is_configured():
            return "AI-enhanced report generation not available. Please configure Claude API key."
        
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Generate a professional digital forensics analysis report based on the following data. Include:
- Executive summary
- Key findings
- Indicators of compromise
- Risk assessment
- Recommendations

Analysis Data:
{json.dumps(analysis_data, indent=2)}"""
                    }
                ]
            )
            return message.content[0].text
        except Exception as e:
            return f"Failed to generate report: {str(e)}"
