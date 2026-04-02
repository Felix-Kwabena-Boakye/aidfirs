from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import Evidence
from .serializers import EvidenceSerializer
from backend.authentication import JWTAuthentication
from accounts.permissions import CanManageEvidence, IsAdmin, IsInvestigator
from django.http import HttpResponse
import os


class EvidenceViewSet(viewsets.ViewSet):
    """
    ViewSet for Evidence using MongoDB with JWT authentication and role-based permissions.
    
    Permissions:
    - Admin: Full access to all evidence
    - Investigator: Can upload/manage evidence
    - Analyst: Can only view evidence
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Return permissions based on action."""
        if self.action in ['create', 'update', 'destroy', 'mark_analyzed']:
            # Only investigators and admins can create/update/delete evidence
            return [IsInvestigator()]
        return [IsAuthenticated()]
    
    def list(self, request):
        """List all evidence. Admin sees all, others see evidence for their cases."""
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role == 'admin':
            evidence = Evidence.get_all()
        else:
            # Filter to only show evidence from user's cases
            from cases.models import Case
            user_cases = Case.get_all()
            user_case_ids = [str(c._id) for c in user_cases if str(c.investigator_id) == user_id]
            all_evidence = Evidence.get_all()
            evidence = [e for e in all_evidence if e.case_id in user_case_ids]
        
        serializer = EvidenceSerializer(evidence, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create new evidence."""
        serializer = EvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            evidence = Evidence.create(
                case_id=serializer.validated_data.get('case_id'),
                evidence_type=serializer.validated_data.get('evidence_type'),
                file_name=serializer.validated_data.get('file_name'),
                file_path=serializer.validated_data.get('file_path'),
                collector_id=str(request.user._id) if hasattr(request.user, '_id') else '',
                description=serializer.validated_data.get('description', ''),
                file_size=serializer.validated_data.get('file_size', 0)
            )
            return Response(
                EvidenceSerializer(evidence).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """Get specific evidence."""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response(
                {'error': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(EvidenceSerializer(evidence).data)
    
    def update(self, request, pk=None):
        """Update evidence."""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response(
                {'error': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        allowed_fields = ['file_name', 'file_path', 'description', 'status', 'tags']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        evidence.update(**update_data)
        
        return Response(EvidenceSerializer(evidence).data)
    
    def destroy(self, request, pk=None):
        """Delete evidence."""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response(
                {'error': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        evidence.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def mark_analyzed(self, request, pk=None):
        """Mark evidence as analyzed."""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response(
                {'error': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        evidence.mark_analyzed()
        return Response(EvidenceSerializer(evidence).data)

    @action(detail=True, methods=['post'])
    def tsk_image(self, request, pk=None):
        """Simulate creating a disk image using FTK Imager"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        
        from forensic_api.tsk_wrapper import create_disk_image
        # In a real app, dest_dir would be a secure storage location
        dest_dir = os.path.dirname(evidence.file_path)
        result = create_disk_image(evidence.file_path, dest_dir)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_partitions(self, request, pk=None):
        """Run mmls to get partitions"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        
        from forensic_api.tsk_wrapper import get_partitions
        result = get_partitions(evidence.file_path)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_files(self, request, pk=None):
        """Run fls to list files in a partition"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        
        offset = request.data.get('offset', '0')
        from forensic_api.tsk_wrapper import list_files
        result = list_files(evidence.file_path, offset)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_extract(self, request, pk=None):
        """Run icat to extract a file"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        
        offset = request.data.get('offset', '0')
        inode = request.data.get('inode')
        if not inode: return Response({"error": "inode required"}, status=status.HTTP_400_BAD_REQUEST)
        
        output_path = f"/tmp/extracted_{evidence._id}_{inode}"
        from forensic_api.tsk_wrapper import extract_file
        result = extract_file(evidence.file_path, inode, output_path, offset)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_timeline(self, request, pk=None):
        """Run mactime to get timeline"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        
        from forensic_api.tsk_wrapper import get_timeline
        result = get_timeline(evidence.file_path)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_recovered_metadata(self, request, pk=None):
        """Run ils to recover deleted metadata"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        
        offset = request.data.get('offset', '0')
        from forensic_api.tsk_wrapper import get_deleted_metadata
        result = get_deleted_metadata(evidence.file_path, offset)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """Generate and download a PDF report for this evidence"""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response(
                {'error': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        from .report_generator import generate_evidence_pdf
        pdf_bytes = generate_evidence_pdf(evidence)
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="evidence_report_{evidence._id}.pdf"'
        return response
