from datetime import datetime
from .indicator_extractor import IndicatorExtractor
from .summarizer import Summarizer
from .anomaly_detector import AnomalyDetector


class AIEngine:

    def __init__(self):
        self.extractor = IndicatorExtractor()
        self.summarizer = Summarizer()
        self.detector = AnomalyDetector()

    def analyze(self, text: str):

        indicators = self.extractor.extract(text)
        summary = self.summarizer.summarize(text)
        anomaly = self.detector.detect(indicators)

        return {
            "analysis_time": datetime.now().isoformat(),
            "summary": summary,
            "indicators": indicators,
            "risk_assessment": anomaly
        }