from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import Case
from .serializers import CaseSerializer
from backend.authentication import JWTAuthentication
from accounts.permissions import CanManageCases, IsAdmin, IsInvestigator
import json
import logging
from evidence.models import Evidence
from evidence.serializers import EvidenceSerializer
from analysis.models import AnalysisResult
from analysis.serializers import AnalysisResultSerializer

logger = logging.getLogger(__name__)

class CaseViewSet(viewsets.ViewSet):
    """
    ViewSet for Cases using MongoDB with JWT authentication and role-based permissions.
    
    Permissions:
    - Admin: Full access to all cases, can delete/archive
    - Investigator: Can create cases, view assigned cases
    - Analyst: Can only view assigned cases
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Return permissions based on action."""
        if self.action == 'destroy' or self.action == 'archive':
            # Only admins can delete/archive cases
            return [IsAdmin()]
        elif self.action in ['create', 'update', 'close', 'assign']:
            # Investigators and admins can create/update
            return [IsInvestigator()]
        return [IsAuthenticated()]
    
    def list(self, request):
        """List all cases. Admins see all, investigators/analysts see their assigned."""
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role == 'admin':
            # Admin can see all cases
            cases = Case.get_all()
        else:
            # Investigators and analysts see only their assigned cases
            cases = Case.get_all()
            cases = [c for c in cases if str(c.investigator_id) == user_id or user_id in getattr(c, 'assigned_to', [])]
        
        serializer = CaseSerializer(cases, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create a new case."""
        serializer = CaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        case = Case.create(
            case_number=serializer.validated_data.get('case_number'),
            title=serializer.validated_data.get('title'),
            description=serializer.validated_data.get('description'),
            investigator_id=str(request.user._id) if hasattr(request.user, '_id') else '',
            priority=serializer.validated_data.get('priority', 'medium'),
            case_type=serializer.validated_data.get('case_type', '')
        )
        
        try:
            from .coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=case._id,
                evidence_id=None,
                action="Evidence upload",  # Wait, using "Evidence upload" or "Case Creation"
                performed_by=username,
                notes=f"Case '{case.title}' created with case number '{case.case_number}'."
            )
            TimelineEvent.create(
                case_id=case._id,
                event_type="Case Event",
                description=f"Case opened by {username}",
                severity="info"
            )
        except Exception:
            pass
        
        return Response(
            CaseSerializer(case).data,
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, pk=None):
        """Get a specific case."""
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Enforce RBAC
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin' and str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', []):
            return Response(
                {'error': 'Permission denied: You are not assigned to this case.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        return Response(CaseSerializer(case).data)
    
    def update(self, request, pk=None):
        """Update a case."""
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Enforce RBAC
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin' and str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', []):
            return Response(
                {'error': 'Permission denied: You are not assigned to this case.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update allowed fields
        allowed_fields = ['title', 'description', 'status', 'priority', 'case_type', 'tags']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        status_before = case.status
        case.update(**update_data)
        
        if status_before != 'closed' and case.status == 'closed':
            try:
                from .coc_models import ChainOfCustody, TimelineEvent
                username = getattr(request.user, 'username', 'unknown')
                ChainOfCustody.create(
                    case_id=case._id,
                    evidence_id=None,
                    action="Case Closed",
                    performed_by=username,
                    notes=f"Case '{case.title}' was marked as closed."
                )
                TimelineEvent.create(
                    case_id=case._id,
                    event_type="Case Closed",
                    description=f"Case closed by {username}",
                    severity="low"
                )
            except Exception:
                pass
        
        return Response(CaseSerializer(case).data)
    
    def destroy(self, request, pk=None):
        """Delete a case."""
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        case.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a case. Admin only."""
        if getattr(request.user, 'role', None) != 'admin':
            return Response(
                {'error': 'Only admins can archive cases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        case.status = 'archived'
        case.save()
        return Response(CaseSerializer(case).data)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign investigators to a case. Admin only."""
        if getattr(request.user, 'role', None) != 'admin':
            return Response(
                {'error': 'Only admins can assign investigators to cases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        investigator_ids = request.data.get('investigator_ids', [])
        case.assigned_to = investigator_ids
        case.save()
        
        try:
            from .coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=case._id,
                evidence_id=None,
                action="Assignment Update",
                performed_by=username,
                notes=f"Assigned investigators updated: {', '.join(investigator_ids)}."
            )
            TimelineEvent.create(
                case_id=case._id,
                event_type="Assignment Update",
                description=f"Investigators assigned: {len(investigator_ids)} assigned",
                severity="info"
            )
        except Exception:
            pass
        
        return Response(CaseSerializer(case).data)
    
    @action(detail=True, methods=['get'])
    def evidence(self, request, pk=None):
        """Get all evidence for a case."""
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Enforce RBAC
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin' and str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', []):
            return Response(
                {'error': 'Permission denied: You are not assigned to this case.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from evidence.models import Evidence
        evidence = Evidence.get_by_case(str(case._id))
        from evidence.serializers import EvidenceSerializer
        return Response(EvidenceSerializer(evidence, many=True).data)

    @action(detail=True, methods=['get'])
    def chain_of_custody(self, request, pk=None):
        """Get all Chain of Custody entries for a case."""
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Enforce RBAC
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin' and str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', []):
            return Response(
                {'error': 'Permission denied: You are not assigned to this case.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .coc_models import ChainOfCustody
        records = ChainOfCustody.get_by_case(str(case._id))
        return Response([r.to_dict() for r in records])

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get all Timeline events for a case."""
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Enforce RBAC
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin' and str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', []):
            return Response(
                {'error': 'Permission denied: You are not assigned to this case.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .coc_models import TimelineEvent
        events = TimelineEvent.get_by_case(str(case._id))
        
        # Support search and filter query parameters
        search_query = request.query_params.get('search', '').lower()
        severity_filter = request.query_params.get('severity', '').lower()
        event_type_filter = request.query_params.get('event_type', '').lower()
        
        filtered_events = []
        for e in events:
            if severity_filter and e.severity.lower() != severity_filter:
                continue
            if event_type_filter and e.event_type.lower() != event_type_filter:
                continue
            if search_query:
                # search in description or event_type
                if search_query not in e.description.lower() and search_query not in e.event_type.lower():
                    continue
            filtered_events.append(e)
            
        return Response([e.to_dict() for e in filtered_events])

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Global search across cases, evidence, and analysis results.
        Enforces Role-Based Access Control (RBAC).
        """
        q = request.query_params.get('q', '').strip()
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        username = getattr(request.user, 'username', 'unknown')

        print(f"[SEARCH] Request received - User: {username} (ID: {user_id}, Role: {user_role})")
        print(f"[SEARCH] Search Query: '{q}'")
        logger.info(f"Global search requested by user {username} (role: {user_role}) with query: '{q}'")

        if not q:
            print("[SEARCH] Empty query, returning empty results.")
            return Response({
                "cases": [],
                "evidence": [],
                "analysis_results": []
            })

        # Step 1: Filter accessible cases based on role
        if user_role == 'admin':
            accessible_cases = Case.get_all()
        else:
            all_cases = Case.get_all()
            accessible_cases = [
                c for c in all_cases 
                if str(c.investigator_id) == user_id or user_id in getattr(c, 'assigned_to', [])
            ]
        
        accessible_case_ids = {str(c._id) for c in accessible_cases}
        print(f"[SEARCH] Total accessible cases for user: {len(accessible_cases)}")

        # Step 2: Search Cases
        matching_cases = []
        for c in accessible_cases:
            if (q.lower() in c.title.lower() or 
                q.lower() in c.case_number.lower() or 
                q.lower() in c.description.lower() or 
                any(q.lower() in tag.lower() for tag in getattr(c, 'tags', []))):
                matching_cases.append(c)

        print(f"[SEARCH] Found {len(matching_cases)} matching cases.")

        # Step 3: Search Evidence
        matching_evidence = []
        try:
            all_evidence = Evidence.get_all()
        except Exception as e:
            logger.error(f"Error fetching evidence during search: {e}")
            all_evidence = []

        for e in all_evidence:
            if str(e.case_id) in accessible_case_ids:
                file_path_lower = e.file_path.lower() if e.file_path else ""
                if (q.lower() in e.file_name.lower() or
                    q.lower() in file_path_lower or
                    q.lower() in e.description.lower() or
                    q.lower() in getattr(e, 'hash_md5', '').lower() or
                    q.lower() in getattr(e, 'hash_sha1', '').lower() or
                    q.lower() in getattr(e, 'hash_sha256', '').lower() or
                    any(q.lower() in tag.lower() for tag in getattr(e, 'tags', []))):
                    matching_evidence.append(e)

        print(f"[SEARCH] Found {len(matching_evidence)} matching evidence items.")

        # Step 4: Search Analysis Results
        matching_analysis = []
        try:
            all_analysis = AnalysisResult.get_all()
        except Exception as e:
            logger.error(f"Error fetching analysis results during search: {e}")
            all_analysis = []

        for ar in all_analysis:
            if str(ar.case_id) in accessible_case_ids:
                findings_str = json.dumps(getattr(ar, 'findings', {}))
                indicators_str = json.dumps(getattr(ar, 'indicators', []))
                if (q.lower() in ar.analysis_type.lower() or
                    q.lower() in ar.severity.lower() or
                    q.lower() in findings_str.lower() or
                    q.lower() in indicators_str.lower() or
                    any(q.lower() in s.lower() for s in getattr(ar, 'summaries', [])) or
                    any(q.lower() in r.lower() for r in getattr(ar, 'recommendations', []))):
                    matching_analysis.append(ar)

        print(f"[SEARCH] Found {len(matching_analysis)} matching analysis results.")

        # Step 5: Serialize and Respond
        serialized_cases = CaseSerializer(matching_cases, many=True).data
        serialized_evidence = EvidenceSerializer(matching_evidence, many=True).data
        serialized_analysis = AnalysisResultSerializer(matching_analysis, many=True).data

        response_payload = {
            "cases": serialized_cases,
            "evidence": serialized_evidence,
            "analysis_results": serialized_analysis
        }
        
        print(f"[SEARCH] Database query results: cases={len(serialized_cases)}, evidence={len(serialized_evidence)}, analysis_results={len(serialized_analysis)}")
        return Response(response_payload)

