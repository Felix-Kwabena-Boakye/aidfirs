import json
from typing import List, Dict, Any

class ThreatMonitor:
    """
    Analyzes forensic evidence for geopolitical risks and coordinate patterns.
    """
    
    CRITICAL_REGIONS = {
        "East Asia": {"center": [39.90, 116.40], "radius": 500, "label": "Beijing / Regional Stability"},
        "Conflict Zone A": {"center": [31.50, 34.46], "radius": 200, "label": "Middle East / High Risk"},
        "Global Commons": {"center": [0, 0], "radius": 0, "label": "Low Risk"}
    }

    def analyze_location_risk(self, metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Correlates GPS metadata with critical regions to assess risk levels.
        """
        threats_found = []
        overall_risk = "Low"
        
        for item in metadata:
            coords = item.get("gps_coords")
            if not coords:
                continue
                
            lat, lon = coords
            for region, data in self.CRITICAL_REGIONS.items():
                center = data["center"]
                # Basic distance heuristic
                dist = ((lat - center[0])**2 + (lon - center[1])**2)**0.5
                if dist < (data["radius"] / 111):  # Approx km to degrees
                    threats_found.append({
                        "file": item.get("name"),
                        "region": region,
                        "label": data["label"],
                        "confidence": "High"
                    })
                    overall_risk = "High" if "Regional" in data["label"] else "Medium"

        return {
            "threats": threats_found,
            "overall_risk_score": 85 if threats_found else 5,
            "status": "Threat Defused" if not threats_found else "Monitoring Pattern",
            "message": "Patterns around sensitive geopolitical nodes identified." if threats_found else "No immediate global threats found."
        }
