from .orchestrator import AIOrchestrator


class AnomalyDetector:

    def __init__(self):
        self.orchestrator = AIOrchestrator()

    def detect(self, indicators: dict, text: str = ""):
        """
        Detect anomalies and assess risk using rule-based analysis and Claude AI.
        
        Args:
            indicators: Extracted indicators dictionary
            text: Original text for context (optional)
            
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
            "risk_level": level
        }

        # Use AI Orchestrator for enhanced risk analysis
        if self.orchestrator:
            try:
                enhanced = self.orchestrator.analyze_risk(indicators, text)
                # Merge enhanced analysis with rule-based
                result["risk_score"] = max(risk_score, enhanced.get("risk_score", risk_score))

                # Update risk level based on enhanced score (or prefer provider)
                provider_level = enhanced.get("risk_level")
                if provider_level:
                    result["risk_level"] = provider_level
                else:
                    if result["risk_score"] >= 7:
                        result["risk_level"] = "Critical"
                    elif result["risk_score"] >= 5:
                        result["risk_level"] = "High"
                    elif result["risk_score"] >= 3:
                        result["risk_level"] = "Medium"
                    else:
                        result["risk_level"] = "Low"

                # Add additional insights (if provided)
                if enhanced.get("risk_factors"):
                    result["risk_factors"] = enhanced["risk_factors"]
                if enhanced.get("recommendations"):
                    result["recommendations"] = enhanced["recommendations"]
                if enhanced.get("method"):
                    result["method"] = enhanced["method"]

            except Exception as e:
                print(f"Claude anomaly detection failed: {e}")

        return result
