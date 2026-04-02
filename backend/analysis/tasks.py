from celery import shared_task
from .models import AnalysisResult
from ..forensic_engine.disk_parser import parse_disk_image
from ..ai_engine.inference import run_ai_analysis

@shared_task
def process_forensic_analysis(evidence_id):
    # Placeholder for forensic processing
    # Integrate with Sleuth Kit, etc.
    result = parse_disk_image(evidence_id)
    AnalysisResult.objects.create(evidence_id=evidence_id, result=result)

@shared_task
def process_ai_analysis(evidence_id):
    # Placeholder for AI analysis
    insights = run_ai_analysis(evidence_id)
    AnalysisResult.objects.create(evidence_id=evidence_id, ai_insights=insights)
