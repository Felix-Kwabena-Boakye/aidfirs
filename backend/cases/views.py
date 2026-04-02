from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import Case
from .serializers import CaseSerializer
from backend.authentication import JWTAuthentication
from accounts.permissions import CanManageCases, IsAdmin, IsInvestigator


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
            cases = [c for c in cases if str(c.investigator_id) == user_id]
        
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
        return Response(CaseSerializer(case).data)
    
    def update(self, request, pk=None):
        """Update a case."""
        case = Case.get_by_id(pk)
        if not case:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update allowed fields
        allowed_fields = ['title', 'description', 'status', 'priority', 'case_type', 'tags']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        case.update(**update_data)
        
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
        
        from evidence.models import Evidence
        evidence = Evidence.get_by_case(str(case._id))
        from evidence.serializers import EvidenceSerializer
        return Response(EvidenceSerializer(evidence, many=True).data)
