from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import Evidence
from .serializers import EvidenceSerializer
from backend.authentication import JWTAuthentication as BackendJWTAuthentication
from accounts.permissions import CanManageEvidence, IsAdmin, IsInvestigator
from django.http import HttpResponse, FileResponse
from pymongo import errors as pymongo_errors
import os
import logging
from django.conf import settings

logger = logging.getLogger("evidence.views")


from forensic_engine.recovery_engine import RecoveryEngine




class EvidenceViewSet(viewsets.ViewSet):

    """
    ViewSet for Evidence using MongoDB with JWT authentication and role-based permissions.
    
    Permissions:
    - Admin: Full access to all evidence
    - Investigator: Can upload/manage evidence
    - Analyst: Can only view evidence
    """
    authentication_classes = [BackendJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Return permissions based on action."""
        if self.action in [
            'create', 'update', 'destroy', 'mark_analyzed',
            'recover_and_analyze', 'restore_files', 'photorec_carve',
            'testdisk_scan', 'autopsy_ingest', 'verify_integrity'
        ]:
            # Only investigators and admins can create/update/delete/recover evidence
            return [IsInvestigator()]
        return [IsAuthenticated()]
    
    def _check_evidence_access(self, request, evidence):
        """Returns True if the user has access to the evidence's case, otherwise False."""
        user_role = getattr(request.user, 'role', 'analyst')
        if user_role == 'admin':
            return True
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        from cases.models import Case
        case = Case.get_by_id(evidence.case_id)
        if not case:
            return False
        return str(case.investigator_id) == user_id or user_id in getattr(case, 'assigned_to', [])

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
            user_case_ids = [str(c._id) for c in user_cases if str(c.investigator_id) == user_id or user_id in getattr(c, 'assigned_to', [])]
            all_evidence = Evidence.get_all()
            evidence = [e for e in all_evidence if e.case_id in user_case_ids]
        
        serializer = EvidenceSerializer(evidence, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create new evidence."""
        serializer = EvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        case_id = serializer.validated_data.get('case_id')
        user_role = getattr(request.user, 'role', 'analyst')
        user_id = str(request.user._id) if hasattr(request.user, '_id') else None
        
        if user_role != 'admin':
            from cases.models import Case
            case = Case.get_by_id(case_id)
            if not case or (str(case.investigator_id) != user_id and user_id not in getattr(case, 'assigned_to', [])):
                return Response(
                    {'error': 'Permission denied: You do not have access to the associated case.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        try:
            evidence = Evidence.create(
                case_id=case_id,
                evidence_type=serializer.validated_data.get('evidence_type'),
                file_name=serializer.validated_data.get('file_name'),
                file_path=serializer.validated_data.get('file_path'),
                collector_id=str(request.user._id) if hasattr(request.user, '_id') else '',
                description=serializer.validated_data.get('description', ''),
                file_size=serializer.validated_data.get('file_size', 0)
            )

            # Determine if Evidence.create() returned an existing duplicate record.
            is_duplicate = "duplicate" in (evidence.tags or [])

            try:
                from cases.coc_models import ChainOfCustody, TimelineEvent
                username = getattr(request.user, 'username', 'unknown')
                action_label = "Duplicate evidence flagged" if is_duplicate else "Evidence upload"
                ChainOfCustody.create(
                    case_id=case_id,
                    evidence_id=str(evidence._id),
                    action=action_label,
                    performed_by=username,
                    notes=f"Evidence file '{evidence.file_name}' {'flagged as duplicate.' if is_duplicate else 'uploaded.'}",
                    hash_before='',
                    hash_after=evidence.hash_sha256
                )
                if not is_duplicate:
                    TimelineEvent.create(
                        case_id=case_id,
                        event_type="File creation",
                        description=f"Evidence file '{evidence.file_name}' uploaded by {username}.",
                        severity="info"
                    )
            except Exception:
                pass

            response_data = EvidenceSerializer(evidence).data

            if is_duplicate:
                # Structured duplicate response — forensic integrity preserved, scanning continues.
                return Response(
                    {
                        "error": "Duplicate evidence detected",
                        "hash": evidence.hash_sha256,
                        "evidence_id": str(evidence._id),
                        "continue": True,
                        "evidence": response_data,
                    },
                    status=status.HTTP_200_OK
                )

            return Response(response_data, status=status.HTTP_201_CREATED)

        except pymongo_errors.DuplicateKeyError as dup:
            # Fallback: E11000 escaped Evidence.create() — surface structured response.
            logger.warning(f"Unhandled E11000 in evidence create view: {dup}")
            return Response(
                {
                    "error": "Duplicate evidence detected",
                    "details": "An evidence record with this hash already exists.",
                    "continue": True,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Evidence create error: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """Get specific evidence."""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response(
                {'error': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if not self._check_evidence_access(request, evidence):
            return Response(
                {'error': 'Permission denied: You do not have access to this evidence\'s case.'},
                status=status.HTTP_403_FORBIDDEN
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
        if not self._check_evidence_access(request, evidence):
            return Response(
                {'error': 'Permission denied: You do not have access to this evidence\'s case.'},
                status=status.HTTP_403_FORBIDDEN
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
        if not self._check_evidence_access(request, evidence):
            return Response(
                {'error': 'Permission denied: You do not have access to this evidence\'s case.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from cases.coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Evidence deletion attempts",
                performed_by=username,
                notes=f"Evidence file '{evidence.file_name}' deletion attempted."
            )
            TimelineEvent.create(
                case_id=evidence.case_id,
                event_type="File deletion",
                description=f"Evidence file '{evidence.file_name}' deleted by {username}.",
                severity="medium"
            )
        except Exception:
            pass
            
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
        if not self._check_evidence_access(request, evidence):
            return Response(
                {'error': 'Permission denied: You do not have access to this evidence\'s case.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        evidence.mark_analyzed()
        return Response(EvidenceSerializer(evidence).data)

    @action(detail=True, methods=['post'])
    def tsk_image(self, request, pk=None):
        """Create a forensic disk image using FTK Imager or dd fallback"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        from forensic_api.tsk_wrapper import create_disk_image
        import os
        from django.conf import settings
        
        # In a real app, dest_dir would be a secure storage location
        dest_dir = os.path.join(settings.BASE_DIR, 'storage')
        os.makedirs(dest_dir, exist_ok=True)
        result = create_disk_image(evidence.file_path, dest_dir)
        
        if result.get('success'):
            evidence.update(file_path=result['image_path'])
            try:
                from cases.coc_models import ChainOfCustody, TimelineEvent
                username = getattr(request.user, 'username', 'unknown')
                ChainOfCustody.create(
                    case_id=evidence.case_id,
                    evidence_id=str(evidence._id),
                    action="Evidence acquisition",
                    performed_by=username,
                    notes=f"Disk image acquired: {result.get('image_path')}.",
                    hash_before=evidence.hash_sha256,
                    hash_after=evidence.hash_sha256
                )
                TimelineEvent.create(
                    case_id=evidence.case_id,
                    event_type="Device insertion",
                    description=f"Storage device imaged successfully by {username}.",
                    severity="info"
                )
            except Exception:
                pass
            
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_partitions(self, request, pk=None):
        """Run mmls to get partitions"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        from forensic_api.tsk_wrapper import get_partitions
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        result = get_partitions(target_path)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_files(self, request, pk=None):
        """Run fls to list files in a partition"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        offset = request.data.get('offset', '0')
        from forensic_api.tsk_wrapper import list_files
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        result = list_files(target_path, offset)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_extract(self, request, pk=None):
        """Run icat to extract a file"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        inode = request.data.get('inode')
        if not inode or not str(inode).isalnum(): 
            return Response({"error": "Invalid inode"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Sanitize offset
        try:
            offset = str(int(request.data.get('offset', '0')))
        except ValueError:
            return Response({"error": "Invalid offset"}, status=status.HTTP_400_BAD_REQUEST)
        
        output_path = f"/tmp/extracted_{evidence._id}_{inode}"
        from forensic_api.tsk_wrapper import extract_file
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        result = extract_file(target_path, inode, output_path, offset)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_timeline(self, request, pk=None):
        """Run mactime to get timeline"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        from forensic_api.tsk_wrapper import get_timeline
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        offset = request.data.get('offset', '0')
        try:
            offset = str(int(offset))
        except (TypeError, ValueError):
            offset = '0'
        result = get_timeline(target_path, partition_offset=offset)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def tsk_recovered_metadata(self, request, pk=None):
        """Run ils to recover deleted metadata"""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        offset = request.data.get('offset', '0')
        from forensic_api.tsk_wrapper import get_deleted_metadata
        result = get_deleted_metadata(evidence.file_path, offset)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def recovery_json(self, request, pk=None):
        """Run forensic recovery and return structured JSON."""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response({'error': 'Evidence not found'}, status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)

        filesystem_type = request.data.get('filesystem_type', 'ntfs')
        file_types = request.data.get('file_types')
        carve = bool(request.data.get('carve', False))
        
        # Sanitize and restrict out_dir to a safe sub-directory
        requested_out_dir = request.data.get('out_dir')
        if requested_out_dir:
            # Prevent path traversal
            safe_base = os.path.join(settings.BASE_DIR, 'storage', 'recoveries')
            os.makedirs(safe_base, exist_ok=True)
            
            # Simple basename to prevent traversal, or just use a generated name
            safe_name = os.path.basename(requested_out_dir)
            out_dir = os.path.join(safe_base, safe_name)
        else:
            out_dir = None

        from backend.forensic_engine.recovery_engine import RecoveryOptions

        use_foremost = bool(request.data.get('use_foremost', False))
        use_scalpel = bool(request.data.get('use_scalpel', False))
        use_bulk_extractor = bool(request.data.get('use_bulk_extractor', False))
        use_plaso = bool(request.data.get('use_plaso', False))
        bulk_plugins = request.data.get('bulk_plugins')

        options = RecoveryOptions(
            file_types=file_types,
            carve=carve,
            out_dir=out_dir,
            use_foremost=use_foremost,
            use_scalpel=use_scalpel,
            use_bulk_extractor=use_bulk_extractor,
            use_plaso=use_plaso,
            bulk_plugins=bulk_plugins,
        )


        engine = RecoveryEngine(options=options)
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        report = engine.recover(image_path=target_path, filesystem_type=filesystem_type)
        
        try:
            from cases.coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Recovery operation",
                performed_by=username,
                notes=f"Recovery engine executed. Filesystem: {filesystem_type}. Carve: {carve}."
            )
            TimelineEvent.create(
                case_id=evidence.case_id,
                event_type="Recovery events",
                description=f"Recovery scanner run by {username}.",
                severity="info"
            )
        except Exception:
            pass
            
        return Response(report, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def tsk_recover_deleted(self, request, pk=None):
        """
        Advanced deleted file recovery with real-time streaming progress
        """
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)

        if hasattr(request, 'data') and request.data is not None:
            offset = request.data.get('offset', '0')
            file_types = request.data.get('file_types', None)
        else:
            offset = getattr(request, 'POST', {}).get('offset', '0') or getattr(request, 'GET', {}).get('offset', '0')
            file_types = getattr(request, 'POST', {}).get('file_types', None) or getattr(request, 'GET', {}).get('file_types', None)

        from django.http import StreamingHttpResponse
        import json

        def event_generator():
            try:
                from forensic_engine.windows_recovery import (
                    scan_recycle_bin, scan_drive_signatures,
                    recover_files_from_recycle_bin
                )
                from forensic_api.tsk_wrapper import get_deleted_metadata

                safe_recoveries_dir = os.path.join(
                    settings.BASE_DIR, 'storage', 'recoveries', str(evidence._id)
                )
                os.makedirs(safe_recoveries_dir, exist_ok=True)

                # --- Step 1: Recycle Bin scan (real deleted files) ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'recycle_bin', 'message': 'Scanning Recycle Bin for deleted files...'})}\n\n"
                recycle_entries = scan_recycle_bin(evidence.file_path)
                restored_files = recover_files_from_recycle_bin(recycle_entries, safe_recoveries_dir)
                recycle_count = len(recycle_entries)
                yield f"data: {json.dumps({'status': 'processing', 'step': 'recycle_bin_done', 'message': f'Recycle Bin scan completed. Found {recycle_count} entry(ies).', 'results': {'recycle_bin_found': recycle_count}})}\n\n"

                # --- Step 2: Raw disk signature carving ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'signatures', 'message': 'Scanning drive sectors for file signatures (max 256MB)...'})}\n\n"
                carved_signatures = scan_drive_signatures(
                    evidence.file_path, file_types=file_types,
                    max_bytes=256 * 1024 * 1024
                )
                sig_count = len(carved_signatures)
                yield f"data: {json.dumps({'status': 'processing', 'step': 'signatures_done', 'message': f'Signature carving completed. Found {sig_count} signature(s).', 'results': {'raw_signatures_found': sig_count}})}\n\n"

                # --- Step 3: TSK metadata (local Recycle Bin fallback if TSK not installed) ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'tsk', 'message': 'Extracting Sleuth Kit (TSK) file system metadata...'})}\n\n"
                tsk_result = get_deleted_metadata(evidence.file_path, offset)
                tsk_count = len(tsk_result.get('metadata', []))
                yield f"data: {json.dumps({'status': 'processing', 'step': 'tsk_done', 'message': f'TSK metadata extraction completed. Found {tsk_count} record(s).', 'results': {'tsk_entries_found': tsk_count}})}\n\n"

                # --- Step 4: FileCarver on .E01 image if available ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'carver', 'message': 'Running signature-based FileCarver on partition...'})}\n\n"
                from forensic_engine.file_carver import FileCarver
                carver = FileCarver()
                carved_metadata = carver.carve_disk_image(evidence.file_path, file_types=file_types)
                carved_files = carver.extract_carved_bytes(evidence.file_path, carved_metadata, safe_recoveries_dir)
                carved_count = len(carved_files)
                yield f"data: {json.dumps({'status': 'processing', 'step': 'carver_done', 'message': f'FileCarver completed. Extracted {carved_count} carved file(s).', 'results': {'carved_files_found': carved_count}})}\n\n"

                # --- Step 5: Filesystem metadata analysis ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'filesystem', 'message': 'Analyzing filesystem index and structures (MFT)...'})}\n\n"
                from forensic_engine.metadata_recovery import DiskImageAnalyzer
                analyzer = DiskImageAnalyzer()
                meta_results = analyzer.full_analysis(evidence.file_path, filesystem_type='ntfs')
                fs_count = len(meta_results.get('recovered_files', []))
                yield f"data: {json.dumps({'status': 'processing', 'step': 'filesystem_done', 'message': f'Filesystem analysis completed. Recovered {fs_count} files.', 'results': {'filesystem_entries_found': fs_count}})}\n\n"

                # --- Step 6: Preparing final report ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'preparing', 'message': 'Compiling forensic recovery report...'})}\n\n"
                is_real = len(recycle_entries) > 0 or len(carved_signatures) > 0
                mock_flag = tsk_result.get('mock', False) and not is_real

                recovery_report = {
                    'success': True,
                    'evidence_id': pk,
                    'mock': mock_flag,
                    'source_path': evidence.file_path,
                    'recycle_bin_files': restored_files,
                    'carved_signatures': carved_signatures[:50],
                    'tsk_metadata': tsk_result.get('metadata', []),
                    'carved_files': carved_files,
                    'filesystem_metadata': meta_results.get('recovered_files', []),
                    'timestamps': meta_results.get('timestamps', []),
                    'statistics': {
                        'recycle_bin_found': len(recycle_entries),
                        'recycle_bin_restored': len([f for f in restored_files if f.get('status') == 'restored']),
                        'raw_signatures_found': len(carved_signatures),
                        'tsk_entries_found': len(tsk_result.get('metadata', [])),
                        'carved_files_found': len(carved_files),
                        'filesystem_entries_found': len(meta_results.get('recovered_files', [])),
                        'total_timestamps': len(meta_results.get('timestamps', [])),
                    },
                    'carving_statistics': carver.get_recovery_statistics(),
                }
                yield f"data: {json.dumps({'status': 'completed', 'data': recovery_report})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'status': 'failed', 'error': str(e)})}\n\n"

        response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        
        # Log recovery action
        try:
            from cases.coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Recovery operation",
                performed_by=username,
                notes="Advanced deleted file recovery scan initiated."
            )
            TimelineEvent.create(
                case_id=evidence.case_id,
                event_type="Recovery events",
                description=f"Advanced recovery scan started by {username}.",
                severity="info"
            )
        except Exception:
            pass
            
        return response

    @action(detail=True, methods=['post'])
    def tsk_recover_specific(self, request, pk=None):
        """
        Recover specific selected files back to their original drive.
        Expects payload: {"filesToRecover": [{"recycle_path": "...", "original_name": "..."}]}
        """
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)

        files_to_recover = request.data.get('filesToRecover', [])
        if not files_to_recover:
            return Response({"error": "No files provided for recovery."}, status=status.HTTP_400_BAD_REQUEST)
            
        import shutil
        import os
        from forensic_engine.windows_recovery import _get_drive_letter
        
        target_drive = _get_drive_letter(evidence.file_path)
        if not target_drive:
            return Response({"error": "Could not determine target pendrive."}, status=status.HTTP_400_BAD_REQUEST)
            
        target_root = f"{target_drive}:\\"
        recovered_files = []
        errors = []
        
        for file_data in files_to_recover:
            src = file_data.get('recycle_path')
            name = file_data.get('original_name') or 'recovered_file'
            
            if not src or not os.path.isfile(src):
                errors.append(f"Source file {src} not found.")
                continue
                
            dest = os.path.join(target_root, os.path.basename(name))
            
            # Avoid overwrite
            counter = 1
            base, ext = os.path.splitext(dest)
            while os.path.exists(dest):
                dest = f"{base}_{counter}{ext}"
                counter += 1
                
            try:
                shutil.copy2(src, dest)
                recovered_files.append(dest)
            except Exception as e:
                errors.append(f"Failed to recover {name}: {str(e)}")
                
        # Log recovery specific action
        try:
            from cases.coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Recovery operation",
                performed_by=username,
                notes=f"Recovered {len(recovered_files)} specific files back to pendrive."
            )
            TimelineEvent.create(
                case_id=evidence.case_id,
                event_type="Recovery events",
                description=f"{len(recovered_files)} files recovered to device by {username}.",
                severity="info"
            )
        except Exception:
            pass
            
        return Response({
            "success": True,
            "recovered": recovered_files,
            "errors": errors
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """Generate and download a PDF report for this evidence"""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response(
                {'error': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
            
        from .report_generator import generate_evidence_pdf
        pdf_bytes = generate_evidence_pdf(evidence)
        
        # Log report & export
        try:
            from cases.coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Report generation",
                performed_by=username,
                notes=f"Evidence report PDF generated."
            )
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Export operations",
                performed_by=username,
                notes=f"Evidence report PDF exported/downloaded."
            )
            TimelineEvent.create(
                case_id=evidence.case_id,
                event_type="File creation",
                description=f"Evidence report downloaded by {username}.",
                severity="info"
            )
        except Exception:
            pass
            
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="evidence_report_{evidence._id}.pdf"'
        return response

    @action(detail=True, methods=['get'], url_path='download-file')
    def download_file(self, request, pk=None):
        """
        Download a recovered file.
        Expects: file_path in query params.
        Validates that the file is within the allowed recovery storage.
        """
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response({"error": "Evidence not found"}, status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
            
        requested_path = request.query_params.get('file_path')
        if not requested_path:
            return Response({"error": "file_path is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Security: Normalize and validate path
        safe_base = os.path.abspath(os.path.join(settings.BASE_DIR, 'storage', 'recoveries'))
        target_path = os.path.abspath(requested_path)
        
        if not target_path.startswith(safe_base):
            return Response({"error": "Access denied: Path outside recovery storage"}, status=status.HTTP_403_FORBIDDEN)
            
        if not os.path.exists(target_path):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
            
        return FileResponse(open(target_path, 'rb'), as_attachment=True, filename=os.path.basename(target_path))

    def _get_real_file_metadata(self, file_path):
        if not os.path.exists(file_path):
            return {}
        
        stat_info = os.stat(file_path)
        size = stat_info.st_size
        
        try:
            import pwd
        except ImportError:
            pwd = None

        # Get timestamps
        import datetime
        created = datetime.datetime.fromtimestamp(stat_info.st_ctime, datetime.timezone.utc).isoformat()
        modified = datetime.datetime.fromtimestamp(stat_info.st_mtime, datetime.timezone.utc).isoformat()
        accessed = datetime.datetime.fromtimestamp(stat_info.st_atime, datetime.timezone.utc).isoformat()
        
        # Owner
        owner = "Unknown"
        if pwd:
            try:
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
            except Exception:
                pass
        else:
            try:
                import win32api
                import win32security
                sd = win32security.GetFileSecurity(file_path, win32security.OWNER_SECURITY_INFORMATION)
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, type = win32security.LookupAccountSid(None, owner_sid)
                owner = f"{domain}\\{name}"
            except Exception:
                owner = f"UID: {stat_info.st_uid}"
                
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1]
        
        metadata = {
            "file_name": name,
            "extension": ext,
            "file_size": size,
            "created_date": created,
            "modified_date": modified,
            "accessed_date": accessed,
            "file_owner": owner,
        }
        
        # ExifTool integration
        try:
            from forensic_api.tsk_wrapper import run_exiftool
            exif_res = run_exiftool(file_path)
            if exif_res.get("success") and not exif_res.get("mock"):
                import json
                exif_data = json.loads(exif_res["output"])[0]
                
                gps_lat = exif_data.get("GPSLatitude") or exif_data.get("GPSPosition")
                gps_lon = exif_data.get("GPSLongitude")
                gps = f"{gps_lat}, {gps_lon}" if gps_lat and gps_lon else (gps_lat or None)
                
                camera = exif_data.get("Model") or exif_data.get("Make")
                device = exif_data.get("Software") or exif_data.get("DeviceName")
                
                if gps:
                    metadata["gps_coordinates"] = gps
                if camera:
                    metadata["camera_information"] = camera
                if device:
                    metadata["device_information"] = device
        except Exception:
            pass
            
        return metadata

    @staticmethod
    def resolve_evidence_file_path(evidence) -> str:
        r"""
        Resolves the actual, valid, server-side absolute file path for an evidence item.
        Guarantees:
        - Rejects client-supplied raw Windows drive letters (C:/, D:/, C:\\, etc.) if they do not exist on the host.
        - Checks for stored evidence files in storage/evidence/, storage/uploads/, /tmp/.
        - Validates file existence, readability, and extension.
        - Raises FileNotFoundError when no real evidence image exists on disk. Never fabricates an evidence image.
        """
        if not evidence:
            raise FileNotFoundError("Evidence object is None")

        raw_path = getattr(evidence, 'file_path', '') or ''
        ev_id = str(getattr(evidence, '_id', ''))
        file_name = getattr(evidence, 'file_name', '') or f"evidence_{ev_id}"

        # 1. Check if raw_path exists as a valid file on local filesystem
        if raw_path and os.path.exists(raw_path) and os.path.isfile(raw_path):
            return os.path.abspath(raw_path)

        # 2. Check Docker container mapped mount path
        from devices.diagnostics import resolve_mapped_path
        mapped = resolve_mapped_path(raw_path)
        if mapped and os.path.exists(mapped) and os.path.isfile(mapped):
            return os.path.abspath(mapped)

        # 3. Check candidate server storage directories
        candidates = [
            os.path.join(settings.BASE_DIR, 'storage', 'evidence', f"{ev_id}.dd"),
            os.path.join(settings.BASE_DIR, 'storage', 'evidence', f"{ev_id}.img"),
            os.path.join(settings.BASE_DIR, 'storage', 'evidence', f"{ev_id}.raw"),
            os.path.join(settings.BASE_DIR, 'storage', 'evidence', f"{ev_id}.E01"),
            os.path.join(settings.BASE_DIR, 'storage', 'evidence', file_name),
            os.path.join(settings.BASE_DIR, 'storage', 'uploads', f"{ev_id}.dd"),
            os.path.join(settings.BASE_DIR, 'storage', 'uploads', file_name),
            f"/tmp/evidence_{ev_id}.dd",
            f"/tmp/evidence_{ev_id}.raw",
            f"/tmp/{file_name}",
        ]

        for cand in candidates:
            if os.path.exists(cand) and os.path.isfile(cand):
                return os.path.abspath(cand)

        # 4. If raw_path is a directory or mount point that exists, search inside for evidence images
        if raw_path and os.path.exists(raw_path) and os.path.isdir(raw_path):
            for root, _, files in os.walk(raw_path):
                for f in files:
                    if f.lower().endswith(('.dd', '.img', '.raw', '.e01', '.iso')):
                        return os.path.abspath(os.path.join(root, f))
            # Directory found but contains no evidence image: raise instead of treating the folder as an image.
            raise FileNotFoundError(
                f"No evidence image found inside directory for ID '{ev_id}'. "
                f"Specified path: '{raw_path}'"
            )

        raise FileNotFoundError(
            f"Evidence file not found on server for ID '{ev_id}'. "
            f"Specified path: '{raw_path}'"
        )


    @action(detail=True, methods=['post'], url_path='recover-and-analyze')
    def recover_and_analyze(self, request, pk=None):
        """
        Runs the full digital forensic recovery and analysis pipeline.
        """
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response({
                'success': False,
                'error': 'Evidence file not found.',
                'details': f'No evidence record found with ID {pk}',
                'code': 'EVIDENCE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        from django.http import StreamingHttpResponse
        import json

        def event_generator():
            try:
                import hashlib
                import datetime
                import time
                from forensic_engine.windows_recovery import (
                    scan_recycle_bin, scan_drive_signatures,
                    recover_files_from_recycle_bin
                )
                from forensic_api.tsk_wrapper import get_deleted_metadata, get_partitions, get_timeline
                from forensic_engine.file_carver import FileCarver
                from forensic_engine.metadata_recovery import DiskImageAnalyzer
                from analysis.assistant import ForensicAIAssistant
                from cases.coc_models import ChainOfCustody, TimelineEvent
                from mongo_connection import get_collection, MONGO_AVAILABLE

                username = getattr(request.user, 'username', 'unknown')
                safe_recoveries_dir = os.path.join(
                    settings.BASE_DIR, 'storage', 'recoveries', str(evidence._id)
                )
                os.makedirs(safe_recoveries_dir, exist_ok=True)

                # --- 1. Verify Device & Resolve Absolute Server Evidence Path ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'connection', 'message': 'Checking evidence file availability'})}\n\n"
                
                try:
                    device_target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
                except FileNotFoundError as fnf_err:
                    yield f"data: {json.dumps({'status': 'failed', 'error': 'Evidence file not found.', 'code': 'EVIDENCE_NOT_FOUND', 'details': str(fnf_err)})}\n\n"
                    return

                if not os.path.exists(device_target_path):
                    yield f"data: {json.dumps({'status': 'failed', 'error': 'Evidence file not found.', 'code': 'EVIDENCE_NOT_FOUND', 'details': f'Resolved path {device_target_path} does not exist.'})}\n\n"
                    return

                yield f"data: {json.dumps({'status': 'processing', 'step': 'connection', 'message': 'Evidence file resolved'})}\n\n"

                time.sleep(0.3)

                # --- 2. Scan HDD/USB Drive ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'scan', 'message': 'Scanning device partitions'})}\n\n"
                part_res = get_partitions(device_target_path)
                yield f"data: {json.dumps({'status': 'processing', 'step': 'scan', 'message': 'Device scan finished'})}\n\n"
                time.sleep(0.3)

                # --- 3. Identify Deleted Files ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'deleted_detection', 'message': 'Scanning for deleted files'})}\n\n"
                recycle_entries = scan_recycle_bin(device_target_path)
                restored_files = recover_files_from_recycle_bin(recycle_entries, safe_recoveries_dir)
                if restored_files:
                    yield f"data: {json.dumps({'status': 'processing', 'step': 'deleted_detection', 'message': f'{len(restored_files)} deleted file(s) restored from recycle metadata'})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'processing', 'step': 'deleted_detection', 'message': 'No deleted files found in recycle metadata'})}\n\n"
                time.sleep(0.3)

                # --- 4. Metadata Extraction ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'metadata_extraction', 'message': 'Extracting metadata from recovered files'})}\n\n"
                time.sleep(0.3)

                # --- 5. Recovery Engine ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'recovery_engine', 'message': 'Running recovery engine (file carving)'})}\n\n"
                carver = FileCarver()
                carved_metadata = carver.carve_disk_image(device_target_path)
                carved_files = carver.extract_carved_bytes(device_target_path, carved_metadata, safe_recoveries_dir)
                time.sleep(0.3)

                # --- 6. Filesystem Analysis ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'filesystem_analysis', 'message': 'Running filesystem analysis'})}\n\n"
                analyzer = DiskImageAnalyzer()
                meta_results = analyzer.full_analysis(device_target_path, filesystem_type='ntfs')
                yield f"data: {json.dumps({'status': 'processing', 'step': 'filesystem_analysis', 'message': 'Filesystem analysis finished'})}\n\n"
                time.sleep(0.3)

                # --- 7. Timeline Reconstruction ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'timeline_reconstruction', 'message': 'Reconstructing timeline from filesystem metadata'})}\n\n"
                timeline_res = get_timeline(device_target_path)
                if isinstance(timeline_res, dict) and timeline_res.get('success') and timeline_res.get('timeline'):
                    yield f"data: {json.dumps({'status': 'processing', 'step': 'timeline_reconstruction', 'message': 'Timeline reconstructed from filesystem metadata'})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'processing', 'step': 'timeline_reconstruction', 'message': 'Timeline reconstruction produced no events for this image'})}\n\n"
                time.sleep(0.3)

                # --- 8. AI Investigation ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'ai_investigation', 'message': 'AI investigation started'})}\n\n"
                time.sleep(0.3)

                # --- 9. Report Generation ---
                yield f"data: {json.dumps({'status': 'processing', 'step': 'report_generation', 'message': 'Report generation started'})}\n\n"

                # Process recovered files lists and calculate checksums
                recovered_list = []
                idx = 0
                for rf in restored_files:
                    path = rf.get('recycle_path')
                    if path and os.path.exists(path):
                        sha256 = hashlib.sha256()
                        sha512 = hashlib.sha512()
                        with open(path, 'rb') as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                sha256.update(chunk)
                                sha512.update(chunk)
                        sha256_hash = sha256.hexdigest()
                        sha512_hash = sha512.hexdigest()
                        
                        meta = self._get_real_file_metadata(path)
                        rec_file = {
                            "id": f"rec_{evidence._id}_{idx}",
                            "file_name": rf.get('original_name'),
                            "file_type": os.path.splitext(rf.get('original_name'))[1] or 'unknown',
                            "original_location": rf.get('recycle_path'),
                            "status": "recovered",
                            "file_size": rf.get('size', 0),
                            "creation_date": meta.get('created_date'),
                            "last_modified_date": meta.get('modified_date'),
                            "recovery_confidence": "Recovered and Validated",
                            "hash_sha256": sha256_hash,
                            "hash_sha512": sha512_hash,
                            "metadata": meta,
                            "provenance": {
                                "source": "recycle_bin_metadata",
                                "process": "AIDFIRS recovery pipeline",
                                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "confidence": "Recovered and Validated",
                                "hash_computed": True,
                            }
                        }
                        recovered_list.append(rec_file)
                        idx += 1

                for cf in carved_files:
                    path = cf.get('carved_path')
                    if path and os.path.exists(path):
                        sha256 = hashlib.sha256()
                        sha512 = hashlib.sha512()
                        with open(path, 'rb') as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                sha256.update(chunk)
                                sha512.update(chunk)
                        sha256_hash = sha256.hexdigest()
                        sha512_hash = sha512.hexdigest()

                        meta = self._get_real_file_metadata(path)
                        rec_file = {
                            "id": f"carve_{evidence._id}_{idx}",
                            "file_name": cf.get('name'),
                            "file_type": os.path.splitext(cf.get('name'))[1] or 'unknown',
                            "original_location": f"Raw sector offset: {cf.get('offset', '0')}",
                            "status": "carved",
                            "file_size": cf.get('size', 0),
                            "creation_date": meta.get('created_date'),
                            "last_modified_date": meta.get('modified_date'),
                            "recovery_confidence": cf.get('recovery_confidence') or 'Unverified Carving Candidate',
                            "hash_sha256": sha256_hash,
                            "hash_sha512": sha512_hash,
                            "metadata": meta,
                            "provenance": {
                                "source": "signature_carving",
                                "process": "AIDFIRS recovery pipeline",
                                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "confidence": cf.get('recovery_confidence') or 'Unverified Carving Candidate',
                                "sector_offset": cf.get('offset', '0'),
                                "hash_computed": True,
                            }
                        }
                        recovered_list.append(rec_file)
                        idx += 1

                # Empty check: never fabricate recovered files when none were recovered.
                if not recovered_list:
                    recovered_list = []

                # Store findings in MongoDB
                if MONGO_AVAILABLE:
                    rec_files_coll = get_collection("recovered_files")
                    metadata_coll = get_collection("metadata")
                    
                    rec_files_coll.delete_many({"evidence_id": str(evidence._id)})
                    metadata_coll.delete_many({"evidence_id": str(evidence._id)})

                    for item in recovered_list:
                        item_doc = item.copy()
                        item_doc["evidence_id"] = str(evidence._id)
                        item_doc["case_id"] = str(evidence.case_id)
                        rec_files_coll.insert_one(item_doc)

                        meta_doc = item["metadata"].copy()
                        meta_doc["recovered_file_id"] = item["id"]
                        meta_doc["evidence_id"] = str(evidence._id)
                        meta_doc["case_id"] = str(evidence.case_id)
                        metadata_coll.insert_one(meta_doc)

                # Generate AI analysis
                assistant = ForensicAIAssistant()
                ai_res = assistant.generate_report(case_context=str(evidence.case_id), forensic_data=str(recovered_list), ai_findings="")

                ai_report_doc = {
                    "case_id": str(evidence.case_id),
                    "evidence_id": str(evidence._id),
                    "findings": ai_res,
                    "generated_at": datetime.datetime.now(datetime.timezone.utc),
                    "performed_by": username
                }
                if MONGO_AVAILABLE:
                    get_collection("ai_reports").insert_one(ai_report_doc)

                # Local fallback writing
                try:
                    rec_files_file = os.path.join(settings.BASE_DIR, 'recovered_files.json')
                    with open(rec_files_file, 'w') as f:
                        json.dump(recovered_list, f, indent=2, default=str)
                except Exception:
                    pass

                # Chain of Custody Auditing
                coc_actions = [
                    ("Device Scan", f"Device scan executed on evidence '{evidence.file_name}'."),
                    ("Metadata Extraction", f"Metadata extraction executed; metadata recorded for {len(recovered_list)} recovered file(s)."),
                    ("Recovery", (f"Recovery engine returned {len(recovered_list)} recovered file(s); hashes computed during recovery."
                                  if recovered_list else "Recovery engine returned no recoverable deleted files.")),
                    ("Report Generation", f"Forensic report generation executed; AI analysis success: {bool(ai_res.get('success'))}.")
                ]
                
                for act_name, act_notes in coc_actions:
                    ChainOfCustody.create(
                        case_id=evidence.case_id,
                        evidence_id=str(evidence._id),
                        action=act_name,
                        performed_by=username,
                        notes=act_notes,
                        hash_before=evidence.hash_sha256,
                        hash_after=evidence.hash_sha256
                    )

                TimelineEvent.create(
                    case_id=evidence.case_id,
                    event_type="Recovery events",
                    description=f"Forensic recovery and analysis pipeline executed on '{evidence.file_name}' by {username}; {len(recovered_list)} file(s) recovered.",
                    severity="info"
                )

                yield f"data: {json.dumps({'status': 'completed', 'recovered_files': recovered_list, 'ai_analysis': ai_res})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'status': 'failed', 'error': str(e)})}\n\n"

        response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    @action(detail=True, methods=['post'], url_path='restore-files')
    def restore_files(self, request, pk=None):
        """
        Restores selected recovered files to a specific target destination.
        """
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response({'error': 'Evidence not found'}, status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        selected_files = request.data.get('files', [])
        destination = request.data.get('destination', 'download_local')

        if not selected_files:
            return Response({"error": "No files selected for restoration."}, status=status.HTTP_400_BAD_REQUEST)

        username = getattr(request.user, 'username', 'unknown')
        from cases.coc_models import ChainOfCustody, TimelineEvent
        
        ChainOfCustody.create(
            case_id=evidence.case_id,
            evidence_id=str(evidence._id),
            action="Restoration",
            performed_by=username,
            notes=f"Restoration process started for {len(selected_files)} files to {destination}."
        )

        restored_paths = []
        errors = []

        if destination in ['original_device', 'usb_drive']:
            import shutil
            from forensic_api.tsk_wrapper import _get_drive_letter
            target_drive = _get_drive_letter(evidence.file_path)
            if not target_drive:
                target_root = os.path.join(settings.BASE_DIR, 'storage', 'restored_drives', destination)
                os.makedirs(target_root, exist_ok=True)
            else:
                target_root = f"{target_drive}:\\"

            for file_info in selected_files:
                name = file_info.get('file_name')
                src_path = file_info.get('original_location')
                
                if not src_path or not os.path.exists(src_path):
                    safe_recoveries_dir = os.path.join(
                        settings.BASE_DIR, 'storage', 'recoveries', str(evidence._id)
                    )
                    src_path = os.path.join(safe_recoveries_dir, name)

                if not os.path.exists(src_path):
                    src_path = evidence.file_path

                dest_path = os.path.join(target_root, os.path.basename(name))
                counter = 1
                base, ext = os.path.splitext(dest_path)
                while os.path.exists(dest_path):
                    dest_path = f"{base}_{counter}{ext}"
                    counter += 1

                try:
                    shutil.copy2(src_path, dest_path)
                    restored_paths.append(dest_path)
                except Exception as e:
                    errors.append(f"Failed to restore {name}: {str(e)}")
        
        elif destination == 'export_location':
            import shutil
            target_root = os.path.join(settings.BASE_DIR, 'storage', 'exports', str(evidence._id))
            os.makedirs(target_root, exist_ok=True)
            
            for file_info in selected_files:
                name = file_info.get('file_name')
                src_path = file_info.get('original_location')
                
                if not src_path or not os.path.exists(src_path):
                    safe_recoveries_dir = os.path.join(
                        settings.BASE_DIR, 'storage', 'recoveries', str(evidence._id)
                    )
                    src_path = os.path.join(safe_recoveries_dir, name)

                if not os.path.exists(src_path):
                    src_path = evidence.file_path

                dest_path = os.path.join(target_root, os.path.basename(name))
                try:
                    shutil.copy2(src_path, dest_path)
                    restored_paths.append(dest_path)
                except Exception as e:
                    errors.append(f"Failed to export {name}: {str(e)}")
            
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Export",
                performed_by=username,
                notes=f"Exported {len(restored_paths)} files to secure export location."
            )
            
        else: # download_local
            for file_info in selected_files:
                restored_paths.append(file_info.get('file_name'))

        if destination == 'download_local':
            action_desc = f"Prepared {len(restored_paths)} recovered file(s) for download by {username}."
        else:
            action_desc = f"Restored {len(restored_paths)} file(s) to {destination} by {username}."

        TimelineEvent.create(
            case_id=evidence.case_id,
            event_type="Recovery events",
            description=action_desc,
            severity="info"
        )

        return Response({
            "success": len(errors) == 0,
            "restored_count": len(restored_paths),
            "restored": restored_paths,
            "errors": errors
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='photorec-carve')
    def photorec_carve(self, request, pk=None):
        """Run PhotoRec file carving on this evidence image."""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        from forensic_api.tsk_wrapper import run_photorec
        # Prepare output directory in safe recoveries folder
        out_dir = os.path.join(settings.BASE_DIR, 'storage', 'recoveries', f"photorec_{evidence._id}")
        os.makedirs(out_dir, exist_ok=True)
        
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        result = run_photorec(target_path, out_dir)
        
        try:
            from cases.coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Recovery operation",
                performed_by=username,
                notes="PhotoRec carving executed."
            )
            TimelineEvent.create(
                case_id=evidence.case_id,
                event_type="Recovery events",
                description=f"PhotoRec carver executed by {username}.",
                severity="info"
            )
        except Exception:
            pass
            
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='testdisk-scan')
    def testdisk_scan(self, request, pk=None):
        """Run TestDisk partition scanning on this evidence image."""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        from forensic_api.tsk_wrapper import run_testdisk
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        result = run_testdisk(target_path)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='autopsy-ingest')
    def autopsy_ingest(self, request, pk=None):
        """Run Autopsy command-line ingest scanner on this evidence image."""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        from forensic_api.tsk_wrapper import run_autopsy_ingest
        target_path = EvidenceViewSet.resolve_evidence_file_path(evidence)
        result = run_autopsy_ingest(target_path)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='exiftool')
    def exiftool(self, request, pk=None):
        """Run ExifTool to extract file metadata."""
        evidence = Evidence.get_by_id(pk)
        if not evidence: return Response(status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied: You do not have access to this case\'s evidence.'}, status=status.HTTP_403_FORBIDDEN)
        
        target_file = request.data.get('file_path')
        if target_file:
            safe_base = os.path.abspath(os.path.join(settings.BASE_DIR, 'storage', 'recoveries'))
            abs_target = os.path.abspath(target_file)
            if not abs_target.startswith(safe_base):
                return Response({"error": "Access denied: Target path outside recoveries directory"}, status=status.HTTP_403_FORBIDDEN)
            file_to_scan = abs_target
        else:
            file_to_scan = EvidenceViewSet.resolve_evidence_file_path(evidence)
            
        from forensic_api.tsk_wrapper import run_exiftool
        result = run_exiftool(file_to_scan)
        
        try:
            from cases.coc_models import ChainOfCustody, TimelineEvent
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Metadata extraction",
                performed_by=username,
                notes=f"Metadata extracted from: {os.path.basename(file_to_scan)}."
            )
            TimelineEvent.create(
                case_id=evidence.case_id,
                event_type="Registry/Metadata Event",
                description=f"Metadata extraction performed by {username}.",
                severity="info"
            )
        except Exception:
            pass
            
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify_integrity')
    def verify_integrity(self, request, pk=None):
        """Verify SHA256 and SHA512 hashes for this evidence."""
        evidence = Evidence.get_by_id(pk)
        if not evidence:
            return Response({'error': 'Evidence not found'}, status=status.HTTP_404_NOT_FOUND)
        if not self._check_evidence_access(request, evidence):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        import hashlib
        
        # Calculate current hashes
        sha256 = hashlib.sha256()
        sha512 = hashlib.sha512()
        
        status_str = "Not verifiable (file missing)"
        current_sha256 = None
        current_sha512 = None
        
        # If file exists, compute real hashes
        if evidence.file_path and os.path.exists(evidence.file_path):
            try:
                with open(evidence.file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
                        sha512.update(chunk)
                current_sha256 = sha256.hexdigest()
                current_sha512 = sha512.hexdigest()
                
                if evidence.hash_sha256 and current_sha256 != evidence.hash_sha256:
                    status_str = "✗ Modified"
                elif evidence.hash_sha256 and current_sha256 == evidence.hash_sha256:
                    status_str = "✓ Verified"
                else:
                    status_str = "Hash computed (no stored hash to compare)"
            except Exception:
                status_str = "Not verifiable (file read error)"
                current_sha256 = None
                current_sha512 = None
        else:
            current_sha256 = None
            current_sha512 = None
            
        is_simulated = not (evidence.file_path and os.path.exists(evidence.file_path))
        
        try:
            from cases.coc_models import ChainOfCustody
            username = getattr(request.user, 'username', 'unknown')
            ChainOfCustody.create(
                case_id=evidence.case_id,
                evidence_id=str(evidence._id),
                action="Evidence Integrity Verification",
                performed_by=username,
                notes=f"Integrity check performed. Result: {status_str}.",
                hash_before=evidence.hash_sha256,
                hash_after=current_sha256
            )
        except Exception:
            pass
            
        return Response({
            "status": status_str,
            "hash_sha256": current_sha256,
            "hash_sha512": current_sha512,
            "original_sha256": evidence.hash_sha256,
            "is_simulated": is_simulated
        }, status=status.HTTP_200_OK)
