"""
Test AI Engine
Tests the AI components: indicator extraction, summarization, anomaly detection
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ai_engine.indicator_extractor import IndicatorExtractor
from ai_engine.summarizer import Summarizer
from ai_engine.anomaly_detector import AnomalyDetector


def test_indicator_extraction():
    """Test indicator extraction from text."""
    print("\n=== Testing Indicator Extraction ===")
    try:
        extractor = IndicatorExtractor()
        
        # Test text with various indicators
        test_text = """
        The malware connected to 192.168.1.100 and sent data to malicious-domain.com.
        File hash: a1b2c3d4e5f6789012345678abcdef12
        Contact email: attacker@evil.com
        URL: http://suspicious-site.com/payload.exe
        """
        
        indicators = extractor.extract(test_text)
        print(f"Extracted indicators: {indicators}")
        
        # Verify indicators were extracted
        assert 'ips' in indicators or 'urls' in indicators or 'hashes' in indicators or 'emails' in indicators
        print("Indicator Extraction: SUCCESS")
        return True
    except Exception as e:
        print(f"Indicator Extraction: FAILED")
        print(f"Error: {e}")
        return False


def test_summarization():
    """Test text summarization."""
    print("\n=== Testing Text Summarization ===")
    try:
        summarizer = Summarizer()
        
        # Test text
        test_text = """
        Digital forensics is the process of uncovering and interpreting electronic data. 
        The goal is to preserve any evidence in its most original form while performing 
        a structured investigation. Digital forensics investigates data theft, fraud, 
        cybercrime, and any other form of electronic evidence-related investigation.
        Forensic analysts use various tools and techniques to recover deleted files, 
        analyze network traffic, and examine system logs.
        """
        
        summary = summarizer.summarize(test_text)
        print(f"Summary: {summary}")
        
        # Verify summary is not empty
        assert summary is not None
        assert len(summary) > 0
        print("Summarization: SUCCESS")
        return True
    except Exception as e:
        print(f"Summarization: FAILED")
        print(f"Error: {e}")
        return False


def test_anomaly_detection():
    """Test anomaly detection."""
    print("\n=== Testing Anomaly Detection ===")
    try:
        detector = AnomalyDetector()
        
        # Test data - indicators dictionary format
        indicators = {
            "ips": ["192.168.1.100", "10.0.0.1"],
            "urls": ["http://malicious.com/payload.exe"],
            "hashes": ["a1b2c3d4e5f6789012345678abcdef12"],
            "emails": ["attacker@evil.com"]
        }
        
        text = "Suspicious connection to malicious domain"
        
        # Test anomaly detection with indicators
        result = detector.detect(indicators, text)
        print(f"Anomaly detection result: {result}")
        
        # Verify result structure
        assert result is not None
        assert 'risk_score' in result or 'risk_level' in result
        print("Anomaly Detection: SUCCESS")
        return True
    except Exception as e:
        print(f"Anomaly Detection: FAILED")
        print(f"Error: {e}")
        return False


def test_ai_engine_integration():
    """Test AI engine integration."""
    print("\n=== Testing AI Engine Integration ===")
    try:
        from ai_engine.engine import AIEngine
        
        engine = AIEngine()
        
        # Test analysis request - engine.analyze expects a string
        test_text = "Suspicious connection to 203.0.113.50 from this machine. Malware detected with hash a1b2c3d4e5f6789012345678abcdef12."
        
        result = engine.analyze(test_text)
        print(f"AI Engine result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
        
        # Verify result structure
        assert result is not None
        assert isinstance(result, dict)
        print("AI Engine Integration: SUCCESS")
        return True
    except Exception as e:
        print(f"AI Engine Integration: FAILED")
        print(f"Error: {e}")
        return False


def run_all_tests():
    """Run all AI engine tests."""
    print("=" * 50)
    print("Running AI Engine Tests")
    print("=" * 50)
    
    results = {
        "Indicator Extraction": test_indicator_extraction(),
        "Summarization": test_summarization(),
        "Anomaly Detection": test_anomaly_detection(),
        "AI Engine Integration": test_ai_engine_integration(),
    }
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
