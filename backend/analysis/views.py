from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdmin, IsInvestigator

from rest_framework.decorators import action
from .models import AnalysisResult
from .serializers import AnalysisResultSerializer
from backend.authentication import JWTAuthentication
from .assistant import ForensicAIAssistant
from ai_engine.system_agent import SystemAgent


class AnalysisResultViewSet(viewsets.ViewSet):
    """
    ViewSet for Analysis Results using MongoDB with JWT authentication.

    RBAC policy:
    - Investigators and admins may run AI analysis endpoints.
    - Analysts may not run analysis endpoints that mutate or generate AI actions.
    - system-execute is admin-only.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Action-level RBAC.

        DRF determines `self.action` from the ViewSet action mapping.
        """
        if self.action in {
            'classify',
            'detect_anomalies',
            'generate_report',
            'evidence_suggestions',
            'predict_recoverability',
        }:
            return [IsInvestigator()]

        if self.action in {'system_execute'}:
            return [IsAdmin()]

        if self.action in {'train_model'}:
            return [IsAdmin()]  # Admin-only can train the AI Oracle


        # Default: authenticated users can read/write analysis results.
        # model_info is read-only and accessible to all authenticated users.
        return [IsAuthenticated()]

    def list(self, request):
        """List all analysis results. Admins see all, others see results for their cases."""
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        all_results = AnalysisResult.get_all()
        if user_role == 'admin':
            results = all_results
        else:
            from cases.models import Case
            user_cases = Case.get_all()
            user_case_ids = [str(c._id) for c in user_cases if str(c.investigator_id) == user_id or user_id in getattr(c, 'assigned_to', [])]
            results = [r for r in all_results if r.case_id in user_case_ids]
            
        serializer = AnalysisResultSerializer(results, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create a new analysis result."""
        serializer = AnalysisResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        case_id = serializer.validated_data.get('case_id')
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin' and case_id:
            from cases.models import Case
            case = Case.get_by_id(case_id)
            if not case or (str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', [])):
                return Response(
                    {'error': 'Permission denied: You do not have access to this case.'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
        result = AnalysisResult.create(
            case_id=case_id,
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
            
        # Enforce RBAC
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin':
            from cases.models import Case
            case_id = result.case_id
            if not case_id and result.evidence_id:
                from evidence.models import Evidence
                evidence = Evidence.get_by_id(result.evidence_id)
                if evidence:
                    case_id = evidence.case_id
            
            if case_id:
                case = Case.get_by_id(case_id)
                if not case or (str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', [])):
                    return Response(
                        {'error': 'Permission denied: You do not have access to this case\'s analysis results.'},
                        status=status.HTTP_403_FORBIDDEN
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
        """Supreme Intelligence Chat: High-integrity neural dispatch."""

        try:
            assistant = ForensicAIAssistant()

            case_context = request.data.get('case_context', '')
            forensic_data = request.data.get('forensic_data', '')
            message = request.data.get('message', '')
            history = request.data.get('history', [])

            if not message:
                return Response(
                    {"error": "Forensic AI Assistant: Neural packet empty. Specify objective."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = assistant.chat(case_context, forensic_data, message, history=history)
            return Response(result)
        except Exception as e:
            return Response(
                {"error": f"Forensic AI Assistant: Neural Link Distortion detected. Realigning cores... ({str(e)})"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'])
    def classify(self, request):
        """Classify files using AI."""
        assistant = ForensicAIAssistant()

        forensic_data = request.data.get('forensic_data', '')
        result = assistant.classify_files(forensic_data)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='detect-anomalies')
    def detect_anomalies(self, request):
        """Detect anomalies using AI."""
        assistant = ForensicAIAssistant()

        forensic_data = request.data.get('forensic_data', '')
        result = assistant.detect_anomalies(forensic_data)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='generate-report')
    def generate_report(self, request):
        """Generate a forensic report using AI."""
        assistant = ForensicAIAssistant()

        case_context = request.data.get('case_context', '')
        forensic_data = request.data.get('forensic_data', '')
        ai_findings = request.data.get('ai_findings', '')
        result = assistant.generate_report(case_context, forensic_data, ai_findings)
        
        # Log report generation CoC action
        try:
            case_id = request.data.get('case_id')
            if case_id:
                from cases.coc_models import ChainOfCustody, TimelineEvent
                username = getattr(request.user, 'username', 'unknown')
                ChainOfCustody.create(
                    case_id=case_id,
                    evidence_id=None,
                    action="Report generation",
                    performed_by=username,
                    notes="AI Forensic report generated."
                )
                TimelineEvent.create(
                    case_id=case_id,
                    event_type="Registry/Metadata Event",
                    description=f"AI Forensic report generated by {username}.",
                    severity="info"
                )
        except Exception:
            pass
            
        return Response(result)

    @action(detail=False, methods=['post'], url_path='system-execute')
    def system_execute(self, request):
        """System Execution Mode: Autonomous system execution."""

        instruction = request.data.get('instruction')
        if not instruction:
            return Response({"error": "No instruction provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        agent = SystemAgent()
        result = agent.execute_instruction(instruction)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='predict-recoverability')
    def predict_recoverability(self, request):
        """
        ML Recoverability Prediction Endpoint.
        Accepts evidence features and returns binary prediction + confidence score.

        POST body:
            evidence_id (optional): link result to an evidence record
            size_bytes (int): file size in bytes
            file_type (str): evidence_type e.g. 'disk_image'
            entropy (float): byte entropy 0.0-8.0
            partition (str): file-system type e.g. 'NTFS'
        """
        from ai_engine.forensic_model import predict_recoverability as ml_predict

        size_bytes = request.data.get('size_bytes', 1024)
        file_type   = request.data.get('file_type', 'file')
        entropy     = request.data.get('entropy', 4.5)
        partition   = request.data.get('partition', 'NTFS')
        evidence_id = request.data.get('evidence_id', '')

        try:
            pred, confidence, anomalies = ml_predict(size_bytes, file_type, entropy, partition)
        except Exception as e:
            return Response(
                {"error": f"ML prediction failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        label = "recoverable" if pred == 1 else "unrecoverable"

        # Optionally write back prediction into analysis_results collection
        if evidence_id:
            try:
                AnalysisResult.create(
                    case_id='',
                    evidence_id=evidence_id,
                    analysis_type='ai',
                    findings={
                        'ai_prediction': pred,
                        'recoverable_label': label,
                        'confidence': round(confidence, 4),
                        'anomalies': anomalies,
                        'features': {
                            'size_bytes': size_bytes,
                            'file_type': file_type,
                            'entropy': entropy,
                            'partition': partition,
                        }
                    },
                    severity='critical' if pred == 0 else 'info',
                    analyzed_by=str(request.user._id) if hasattr(request.user, '_id') else '',
                )
            except Exception:
                pass  # Write-back failure is non-critical

        return Response({
            "prediction": pred,
            "label": label,
            "confidence": round(confidence * 100, 2),
            "anomalies": anomalies,
            "features": {
                "size_bytes": size_bytes,
                "file_type": file_type,
                "entropy": entropy,
                "partition": partition,
            }
        })

    @action(detail=False, methods=['get'], url_path='model-info')
    def model_info(self, request):
        """
        Returns metadata about the currently active Scikit-Learn forensic model.
        Includes model name, accuracy, F1, training date, and features used.
        """
        from ai_engine.forensic_model import load_ml_model
        from mongo_connection import get_ai_models_collection

        ai_models_col = get_ai_models_collection()
        model_meta = None

        if ai_models_col is not None:
            try:
                doc = ai_models_col.find_one(
                    {"model_name": "random_forest_recoverability", "status": "active"},
                    {"model_bytes": 0}  # exclude binary blob from response
                )
                if doc:
                    model_meta = {
                        "model_name": doc.get("model_name"),
                        "trained_at": doc.get("trained_at").isoformat() if doc.get("trained_at") else None,
                        "accuracy": round(float(doc.get("accuracy", 0)), 4),
                        "precision": round(float(doc.get("precision", 0)), 4),
                        "recall": round(float(doc.get("recall", 0)), 4),
                        "f1": round(float(doc.get("f1", 0)), 4),
                        "features": doc.get("features", []),
                        "status": doc.get("status"),
                    }
            except Exception as e:
                pass

        if model_meta is None:
            # Check in-memory cached model
            ml_info = load_ml_model()
            if ml_info.get("model"):
                model_meta = {
                    "model_name": "random_forest_recoverability",
                    "trained_at": ml_info["trained_at"].isoformat() if ml_info.get("trained_at") else None,
                    "accuracy": round(float(ml_info.get("accuracy", 0)), 4),
                    "features": ml_info.get("features", []),
                    "status": "cached",
                }
            else:
                model_meta = {
                    "model_name": None,
                    "status": "no_model_loaded",
                    "message": "No trained model available. Run the training pipeline first."
                }

        return Response(model_meta)

    @action(detail=False, methods=['post'], url_path='train-model')
    def train_model(self, request):
        """
        Triggers training of the Scikit-Learn Random Forest model.
        Admin only.
        """
        from ai_engine.export_pipeline import export_dataset
        from ai_engine.train_model import train_and_save_model
        from ai_engine.forensic_model import load_ml_model
        import ai_engine.forensic_model as fm
        
        try:
            # 1. Export fresh dataset
            export_dataset()
            
            # 2. Train model
            train_and_save_model()
            
            # 3. Clear memory cache to force reload
            fm._cached_ml_model = None
            
            # 4. Load the newly trained model info
            ml_info = load_ml_model()
            
            # 5. Get model info from database or local
            from mongo_connection import get_ai_models_collection
            ai_models_col = get_ai_models_collection()
            model_doc = None
            if ai_models_col is not None:
                model_doc = ai_models_col.find_one({"model_name": "random_forest_recoverability", "status": "active"})
            
            if model_doc:
                metrics = {
                    "accuracy": round(float(model_doc.get("accuracy", 0)), 4),
                    "precision": round(float(model_doc.get("precision", 0)), 4),
                    "recall": round(float(model_doc.get("recall", 0)), 4),
                    "f1": round(float(model_doc.get("f1", 0)), 4),
                    "trained_at": model_doc.get("trained_at").isoformat() if model_doc.get("trained_at") else None,
                    "features": model_doc.get("features", []),
                    "status": "active"
                }
            else:
                metrics = {
                    "accuracy": round(float(ml_info.get("accuracy", 0)), 4),
                    "precision": round(float(ml_info.get("precision", 0)), 4),
                    "recall": round(float(ml_info.get("recall", 0)), 4),
                    "f1": round(float(ml_info.get("f1", 0)), 4),
                    "trained_at": ml_info.get("trained_at").isoformat() if ml_info.get("trained_at") else None,
                    "features": ml_info.get("features", []),
                    "status": "cached"
                }
                
            # Layman-friendly explanations
            explanations = [
                "The AI model analyzes files using four main clues: file size, file type, file system type (partition), and entropy (a measure of file complexity/encryption).",
                f"Training completed successfully! The model reached an accuracy of {metrics['accuracy'] * 100:.2f}%. This means it correctly predicts whether a file can be recovered in {metrics['accuracy'] * 100:.1f} out of 100 cases.",
                "It learned that files with high entropy (complexity) above 7.1 are very likely encrypted or corrupted, making them harder to recover, while log files and registry entries are generally easy to recover."
            ]
            
            return Response({
                "success": True,
                "message": "AI model training completed successfully.",
                "metrics": metrics,
                "explanations": explanations
            })
            
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Failed to train AI model: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

