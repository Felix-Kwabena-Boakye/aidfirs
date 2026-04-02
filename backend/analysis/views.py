from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import AnalysisResult
from .serializers import AnalysisResultSerializer
from backend.authentication import JWTAuthentication
from .assistant import ForensicAIAssistant


class AnalysisResultViewSet(viewsets.ViewSet):
    """
    ViewSet for Analysis Results using MongoDB with JWT authentication.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List all analysis results."""
        results = AnalysisResult.get_all()
        serializer = AnalysisResultSerializer(results, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create a new analysis result."""
        serializer = AnalysisResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = AnalysisResult.create(
            case_id=serializer.validated_data.get('case_id'),
            evidence_id=serializer.validated_data.get('evidence_id'),
            analysis_type=serializer.validated_data.get('analysis_type'),
            findings=serializer.validated_data.get('findings', {}),
            severity=serializer.validated_data.get('severity', 'info'),
            analyzed_by=str(request.user._id) if hasattr(request.user, '_id') else ''
        )
        
        return Response(
            AnalysisResultSerializer(result).data,
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, pk=None):
        """Get a specific analysis result."""
        result = AnalysisResult.get_by_id(pk)
        if not result:
            return Response(
                {'error': 'Analysis result not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(AnalysisResultSerializer(result).data)
    
    def update(self, request, pk=None):
        """Update an analysis result."""
        result = AnalysisResult.get_by_id(pk)
        if not result:
            return Response(
                {'error': 'Analysis result not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        allowed_fields = ['status', 'findings', 'severity', 'conclusion']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        result.update(**update_data)
        
        return Response(AnalysisResultSerializer(result).data)
    
    def destroy(self, request, pk=None):
        """Delete an analysis result."""
        result = AnalysisResult.get_by_id(pk)
        if not result:
            return Response(
                {'error': 'Analysis result not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        result.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark analysis as complete."""
        result = AnalysisResult.get_by_id(pk)
        if not result:
            return Response(
                {'error': 'Analysis result not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        result.complete()
        return Response(AnalysisResultSerializer(result).data)

    @action(detail=False, methods=['post'], url_path='evidence-suggestions')
    def evidence_suggestions(self, request):
        """
        Provide AI-powered suggestions for evidence file name and description.
        Expects: case_context in request.data
        """
        case_context = request.data.get('case_context', '')
        
        # Simple simulation of AI suggestions
        # In a real app, this would call an LLM (Claude, etc.)
        if "Forensic Examination" in case_context:
            file_name = "Physical_Disk_Image_001.E01"
            description = f"High-integrity forensic acquisition for: {case_context.split(',')[0]}"
        elif "Mobile" in case_context.lower():
            file_name = "Mobile_Acquisition_Report.tar"
            description = "Logical extraction of mobile device data and application artifacts."
        else:
            file_name = "Digital_Evidence_Source.E01"
            description = "Forensic acquisition of the digital evidence source for the current case."
            
        return Response({
            "fileName": file_name,
            "description": description
        })

    @action(detail=False, methods=['post'])
    def chat(self, request):
        """
        Chat with the AI forensic assistant.
        Expects: case_context, forensic_data, message in request.data
        """
        assistant = ForensicAIAssistant()
        
        case_context = request.data.get('case_context', '')
        forensic_data = request.data.get('forensic_data', '')
        message = request.data.get('message', '')
        history = request.data.get('history', [])
        
        if not message:
            return Response(
                {"error": "Message is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        result = assistant.chat(case_context, forensic_data, message, history=history)
        
        if not result["success"]:
            return Response(
                {"error": result["error"]}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        return Response({"response": result["response"]})

    @action(detail=False, methods=['post'])
    def classify(self, request):
        """
        Classify files using AI.
        """
        assistant = ForensicAIAssistant()
        forensic_data = request.data.get('forensic_data', '')
        result = assistant.classify_files(forensic_data)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='detect-anomalies')
    def detect_anomalies(self, request):
        """
        Detect anomalies using AI.
        """
        assistant = ForensicAIAssistant()
        forensic_data = request.data.get('forensic_data', '')
        result = assistant.detect_anomalies(forensic_data)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='generate-report')
    def generate_report(self, request):
        """
        Generate a forensic report using AI.
        """
        assistant = ForensicAIAssistant()
        case_context = request.data.get('case_context', '')
        forensic_data = request.data.get('forensic_data', '')
        ai_findings = request.data.get('ai_findings', '')
        result = assistant.generate_report(case_context, forensic_data, ai_findings)
        return Response(result)
