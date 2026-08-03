from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdmin, IsInvestigator

import re
from rest_framework.decorators import action
from .models import AnalysisResult
from .serializers import AnalysisResultSerializer
from backend.authentication import JWTAuthentication
from .assistant import ForensicAIAssistant
from ai_engine.system_agent import SystemAgent
from cases.models import Case


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
        case_context = (request.data.get('case_context', '') or '').strip()

        # Resolve the real case record so suggestions are derived from actual
        # case data, not canned strings.
        case = None
        if case_context:
            case = Case.get_by_id(case_context)
            if case is None:
                case = Case.get_by_id(case_context.replace('-', ''))
            if case is None:
                for candidate in Case.get_all():
                    if (case_context.lower() in (candidate.title or '').lower()
                            or case_context.lower() in (candidate.case_number or '').lower()):
                        case = candidate
                        break

        if case is not None:
            title = (case.title or '').strip()
            desc = (case.description or '').strip()
            device_name = title.replace("Forensic Examination:", "").strip()
            if not device_name:
                device_name = "Digital_Evidence"
            safe_name = re.sub(r'[^\w\-\. ]+', '', device_name).strip().replace(' ', '_')
            file_name = f"{safe_name}_Forensic_Image.E01"
            description = (desc[:500] if desc else
                           f"Forensic acquisition of {device_name} for case {case.case_number}.")
        elif case_context:
            safe_name = re.sub(r'[^\w\-\. ]+', '', case_context).strip().replace(' ', '_')[:120]
            file_name = f"{safe_name}_Forensic_Image.E01"
            description = f"Forensic acquisition of the digital evidence source for: {case_context}"
        else:
            return Response(
                {'error': 'No case context provided to generate suggestions'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
                {"error": f"Forensic AI Assistant analysis failed: {str(e)}"},
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
        
        # Log report generation CoC action (honest about outcome)
        try:
            case_id = request.data.get('case_id')
            if case_id:
                from cases.coc_models import ChainOfCustody, TimelineEvent
                username = getattr(request.user, 'username', 'unknown')
                report_ok = bool(result.get("success"))
                notes = "AI Forensic report generated." if report_ok else "AI Forensic report generation returned insufficient evidence."
                event_desc = f"AI Forensic report generated by {username}." if report_ok else f"AI Forensic report returned insufficient evidence for {username}."
                ChainOfCustody.create(
                    case_id=case_id,
                    evidence_id=None,
                    action="Report generation",
                    performed_by=username,
                    notes=notes
                )
                TimelineEvent.create(
                    case_id=case_id,
                    event_type="Registry/Metadata Event",
                    description=event_desc,
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

        # No trusted trained model: return an honest heuristic status with a null
        # confidence and verified=false. Never fabricate a recoverability score.
        if pred is None:
            return Response({
                "status": "heuristic",
                "confidence": None,
                "verified": False,
                "message": (
                    "No trusted, provenance-verified ML model is loaded. "
                    "No recoverability prediction was produced. "
                    "Train a model on real labelled evidence before requesting predictions."
                ),
                "features": {
                    "size_bytes": size_bytes,
                    "file_type": file_type,
                    "entropy": entropy,
                    "partition": partition,
                }
            }, status=status.HTTP_200_OK)

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
                        'verified': True,
                        'features': {
                            'size_bytes': size_bytes,
                            'file_type': file_type,
                            'entropy': entropy,
                            'partition': partition,
                        }
                    },
                    severity='info',
                    analyzed_by=str(request.user._id) if hasattr(request.user, '_id') else '',
                )
            except Exception:
                pass  # Write-back failure is non-critical

        return Response({
            "status": "model_based",
            "prediction": pred,
            "label": label,
            "confidence": round(confidence * 100, 2),
            "verified": True,
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
                        "data_source": doc.get("data_source"),
                        "real_rows": doc.get("real_rows"),
                        "synthetic_rows": doc.get("synthetic_rows"),
                        "training_method": doc.get("training_method"),
                        "status": doc.get("status"),
                    }
                    if not doc.get("training_method") or doc.get("data_source") == "synthetic":
                        model_meta["trusted"] = False
                        model_meta["message"] = (
                            "This model lacks verifiable provenance or was trained on synthetic-only data. "
                            "Predictions from it are not served. Train on real labelled evidence."
                        )
                    else:
                        model_meta["trusted"] = True
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
                    "data_source": (ml_info.get("provenance") or {}).get("data_source"),
                    "real_rows": (ml_info.get("provenance") or {}).get("real_rows"),
                    "synthetic_rows": (ml_info.get("provenance") or {}).get("synthetic_rows"),
                    "training_method": (ml_info.get("provenance") or {}).get("training_method"),
                    "trusted": ml_info.get("trusted", False),
                    "status": "cached",
                }
                if not ml_info.get("trusted", False):
                    model_meta["message"] = (
                        "This cached model lacks verifiable provenance or was trained on synthetic-only data. "
                        "Predictions from it are not served. Train on real labelled evidence."
                    )
            else:
                model_meta = {
                    "model_name": None,
                    "status": "no_model_loaded",
                    "trusted": False,
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
            # 1. Export fresh dataset (returns provenance: data_source, real/synthetic row counts)
            provenance = export_dataset()
            
            # 2. Train model — refuses when the dataset is synthetic-only
            train_result = train_and_save_model(provenance=provenance)
            
            if train_result.get("status") == "refused":
                return Response({
                    "success": False,
                    "status": "refused",
                    "reason": train_result.get("reason", "Synthetic-only dataset"),
                    "provenance": {
                        "data_source": provenance.get("data_source"),
                        "total_rows": provenance.get("total_rows"),
                        "real_rows": provenance.get("real_rows"),
                        "synthetic_rows": provenance.get("synthetic_rows"),
                    },
                    "message": (
                        "Training was refused because no real labelled evidence was available. "
                        "A model trained on synthetic data would not produce verified forensic "
                        "predictions. Acquire real evidence with recoverability labels first."
                    ),
                }, status=status.HTTP_200_OK)
            
            metrics = train_result.get("metrics", {})
            provenance_out = train_result.get("provenance", {})
            
            # Clear memory cache to force reload of the freshly trained model
            fm._cached_ml_model = None
            load_ml_model()
            
            # Layman-friendly, evidence-based explanations (no fabricated claims)
            training_method = provenance_out.get("training_method", "unknown")
            if training_method == "real":
                method_note = (
                    f"Trained exclusively on {provenance_out.get('real_rows')} real labelled evidence row(s)."
                )
            elif training_method == "real_with_synthetic_supplement":
                method_note = (
                    f"Trained on {provenance_out.get('real_rows')} real labelled evidence row(s) "
                    f"supplemented with {provenance_out.get('synthetic_rows')} synthesized row(s). "
                    "Reported metrics are computed on this mixed dataset and are not a verified "
                    "real-world measure."
                )
            else:
                method_note = "Training dataset provenance could not be verified."
                
            explanations = [
                "The AI model analyzes files using four features: file size, file type, file system type (partition), and byte entropy (a measure of file complexity/encryption).",
                method_note,
                "Re-train the model as real, labelled evidence accumulates so predictions become verified and production-ready.",
            ]
            
            return Response({
                "success": True,
                "status": "trained",
                "message": "AI model training completed successfully.",
                "metrics": metrics,
                "provenance": {
                    "data_source": provenance_out.get("data_source"),
                    "total_rows": provenance_out.get("total_rows"),
                    "real_rows": provenance_out.get("real_rows"),
                    "synthetic_rows": provenance_out.get("synthetic_rows"),
                    "training_method": training_method,
                },
                "explanations": explanations
            })
            
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Failed to train AI model: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

