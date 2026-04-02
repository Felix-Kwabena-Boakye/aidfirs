from datetime import datetime, timezone
from mongo_connection import analysis_results_collection
from .engine import AIEngine


class AIAnalysisService:

    def __init__(self):
        self.engine = AIEngine()
        self.collection = analysis_results_collection

    def analyze_and_store(self, case_id: str, text: str):

        result = self.engine.analyze(text)

        document = {
            "case_id": case_id,
            "analysis": result,
            "created_at": datetime.now(timezone.utc)
        }

        inserted = self.collection.insert_one(document)

        return {
            "analysis_id": str(inserted.inserted_id),
            "result": result
        }
    
    def get_analysis(self, analysis_id: str):
        """Get analysis by ID."""
        from bson import ObjectId
        return self.collection.find_one({"_id": ObjectId(analysis_id)})
    
    def get_analyses_by_case(self, case_id: str):
        """Get all analyses for a case."""
        return list(self.collection.find({"case_id": case_id}))
    
    def get_all_analyses(self):
        """Get all analyses."""
        return list(self.collection.find())
