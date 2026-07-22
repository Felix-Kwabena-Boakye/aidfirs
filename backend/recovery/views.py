import os
import hashlib
import mimetypes
import csv
import zipfile
import io
import re
from datetime import datetime, timezone
from django.http import FileResponse, StreamingHttpResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from .models import RecoveryJob, RecoveredFile, TimelineEvent
from .serializers import RecoveryJobSerializer, RecoveredFileSerializer
from devices.models import Device
from cases.models import Case
from cases.coc_models import ChainOfCustody
from accounts.models import AuditLog

# Storage root for uploaded files
STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage', 'recoveries')

# Safe filename validator
SAFE_FILENAME_RE = re.compile(r'[^\w\s\-\.]')


def sanitize_filename(name):
    """Prevent path traversal and illegal characters."""
    name = os.path.basename(name)  # strip any directory component
    name = SAFE_FILENAME_RE.sub('_', name)
    return name or "unnamed_file"


def get_client_ip(request):
    """Extract client IP address from request headers or remote address."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _log_timeline(case_id, event_type, description, actor=None, device_id=None, evidence_id=None, metadata=None):
    """Helper to log a timeline event."""
    try:
        TimelineEvent.create(
            case_id=case_id,
            event_type=event_type,
            description=description,
            actor=actor,
            device_id=device_id,
            evidence_id=evidence_id,
            metadata=metadata or {}
        )
    except Exception as e:
        print(f"[Timeline] Failed to log event: {e}")


class RecoveryStartView(APIView):
    """
    POST /api/recovery/start/
    Initiate a new recovery job for a device.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_id = request.data.get("device_id")
        case_id = request.data.get("case_id")
        recovery_type = request.data.get("recovery_type", "full")

        if not device_id or not case_id:
            return Response({"success": False, "error": "device_id and case_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Verify device and case exist
        device = Device.get_by_id(device_id)
        case = Case.get_by_id(case_id)
        if not device:
            return Response({"success": False, "error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        if not case:
            return Response({"success": False, "error": "Case not found"}, status=status.HTTP_404_NOT_FOUND)

        # Create job
        job = RecoveryJob.create(device_id=device_id, case_id=case_id, recovery_type=recovery_type)

        # Log CoC and Audit events
        AuditLog.log(
            user_id=str(request.user._id),
            username=request.user.username,
            action="RECOVERY_STARTED",
            resource_type="recovery_job",
            resource_id=str(job._id),
            details={"case_id": case_id, "device_id": device_id, "recovery_type": recovery_type}
        )
        ChainOfCustody.create(
            case_id=case_id,
            evidence_id=device_id,
            action="RECOVERY_STARTED",
            performed_by=request.user.username,
            notes=f"Recovery job {job._id} started for device {device.device_name}. Type: {recovery_type}.",
            ip_address=get_client_ip(request),
        )
        _log_timeline(
            case_id=case_id,
            event_type="RECOVERY_STARTED",
            description=f"Recovery job started for device '{device.device_name}'. Type: {recovery_type}.",
            actor=request.user.username,
            device_id=device_id,
            evidence_id=str(job._id),
        )

        return Response({
            "success": True,
            "message": "Recovery job created and pending agent acquisition.",
            "job": job.to_dict()
        }, status=status.HTTP_201_CREATED)


class PendingJobsView(APIView):
    """
    GET /api/recovery/jobs/pending/
    Called by local agents to find jobs to execute.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jobs = RecoveryJob.get_pending()
        return Response({
            "success": True,
            "jobs": [j.to_dict() for j in jobs]
        })


class RecoveryJobListView(APIView):
    """
    GET /api/recovery/jobs/
    Lists all recovery jobs. Supports filtering by case_id, device_id, status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        device_id = request.query_params.get("device_id")
        job_status = request.query_params.get("status")
        limit = int(request.query_params.get("limit", 100))

        jobs = RecoveryJob.get_all(
            case_id=case_id,
            device_id=device_id,
            status=job_status,
            limit=limit
        )
        return Response({
            "success": True,
            "count": len(jobs),
            "jobs": [j.to_dict() for j in jobs]
        })


class RecoveryJobDetailView(APIView):
    """
    GET /api/recovery/jobs/<id>/
    PATCH /api/recovery/jobs/<id>/
    Get details or update a recovery job status, progress, stage, files_found.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = RecoveryJob.get_by_id(pk)
        if not job:
            return Response({"success": False, "error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "job": job.to_dict()})

    def patch(self, request, pk):
        job = RecoveryJob.get_by_id(pk)
        if not job:
            return Response({"success": False, "error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        # Allowed fields
        status_val = request.data.get("status")
        stage = request.data.get("stage")
        progress = request.data.get("progress")
        files_found = request.data.get("files_found")
        error_message = request.data.get("error_message")
        current_operation = request.data.get("current_operation")

        updates = {}
        if status_val:
            updates["status"] = status_val
            if status_val in ("COMPLETED", "FAILED"):
                updates["completion_time"] = datetime.now(timezone.utc)
                # Log timeline event on completion
                try:
                    _log_timeline(
                        case_id=job.case_id,
                        event_type=f"RECOVERY_{status_val}",
                        description=f"Recovery job {pk} {status_val.lower()}. Files found: {job.files_found}.",
                        device_id=job.device_id,
                        evidence_id=str(pk),
                    )
                except Exception:
                    pass
        if stage:
            updates["stage"] = stage
            if current_operation is None:
                updates["current_operation"] = RecoveryJob.STAGE_OPERATIONS.get(
                    stage, stage.replace('_', ' ').title()
                )
        if progress is not None:
            updates["progress"] = int(progress)
        if files_found is not None:
            updates["files_found"] = int(files_found)
        if error_message is not None:
            updates["error_message"] = error_message
        if current_operation is not None:
            updates["current_operation"] = current_operation

        job.update(**updates)

        return Response({
            "success": True,
            "job": job.to_dict()
        })


class RecoveredFileUploadView(APIView):
    """
    POST /api/recovery/jobs/<id>/upload/
    Uploads a carved/recovered file binary and registers it with full forensic metadata.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, pk):
        job = RecoveryJob.get_by_id(pk)
        if not job:
            return Response({"success": False, "error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"success": False, "error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        hash_sha256 = request.data.get("hash_sha256", "").strip()
        hash_sha512 = request.data.get("hash_sha512", "").strip()
        hash_md5 = request.data.get("hash_md5", "").strip()
        hash_sha1 = request.data.get("hash_sha1", "").strip()
        raw_filename = request.data.get("filename", uploaded_file.name).strip()
        filename = sanitize_filename(raw_filename)

        # Extended forensic metadata
        original_path = request.data.get("original_path", "")
        recovery_method = request.data.get("recovery_method", "signature_carving")
        recovery_status = request.data.get("recovery_status", "recovered")
        created_time = request.data.get("created_time")
        modified_time = request.data.get("modified_time")
        accessed_time = request.data.get("accessed_time")
        deleted_time = request.data.get("deleted_time")
        device_id = request.data.get("device_id") or job.device_id
        examiner = request.data.get("examiner", request.user.username)
        carve_offset = request.data.get("carve_offset")
        description = request.data.get("description", "")

        # Save to filesystem
        os.makedirs(STORAGE_ROOT, exist_ok=True)
        job_dir = os.path.join(STORAGE_ROOT, str(job._id))
        os.makedirs(job_dir, exist_ok=True)

        safe_filename = sanitize_filename(filename)
        dest_path = os.path.join(job_dir, safe_filename)

        # Handle duplicate filenames
        counter = 1
        base, ext = os.path.splitext(dest_path)
        while os.path.exists(dest_path):
            dest_path = f"{base}_{counter}{ext}"
            counter += 1

        # Calculate hashes on the fly
        sha256_calc = hashlib.sha256()
        sha512_calc = hashlib.sha512()
        md5_calc = hashlib.md5()
        sha1_calc = hashlib.sha1()

        try:
            with open(dest_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
                    sha256_calc.update(chunk)
                    sha512_calc.update(chunk)
                    md5_calc.update(chunk)
                    sha1_calc.update(chunk)
        except Exception as e:
            return Response({"success": False, "error": f"Failed to save file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        final_sha256 = hash_sha256 or sha256_calc.hexdigest()
        final_sha512 = hash_sha512 or sha512_calc.hexdigest()
        final_md5 = hash_md5 or md5_calc.hexdigest()
        final_sha1 = hash_sha1 or sha1_calc.hexdigest()
        file_size = os.path.getsize(dest_path)

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(dest_path)
        file_extension = os.path.splitext(safe_filename)[1].lower().lstrip('.')

        # Create model in MongoDB
        recovered_file = RecoveredFile.create(
            filename=os.path.basename(dest_path),
            storage_location=dest_path,
            hash_sha256=final_sha256,
            hash_sha512=final_sha512,
            hash_md5=final_md5,
            hash_sha1=final_sha1,
            size=file_size,
            case_id=job.case_id,
            recovery_job_id=str(job._id),
            original_path=original_path,
            recovered_path=dest_path,
            file_extension=file_extension,
            mime_type=mime_type,
            recovery_method=recovery_method,
            recovery_status=recovery_status,
            created_time=created_time,
            modified_time=modified_time,
            accessed_time=accessed_time,
            deleted_time=deleted_time,
            device_id=device_id,
            examiner=examiner,
            carve_offset=carve_offset,
            description=description,
        )

        # Log CoC events
        try:
            ChainOfCustody.create(
                case_id=job.case_id,
                evidence_id=job.device_id,
                action="FILE_RECOVERED",
                performed_by=request.user.username,
                notes=f"File recovered: {recovered_file.filename} (Size: {recovered_file.size} bytes, Method: {recovery_method}).",
                hash_after=final_sha256
            )
            ChainOfCustody.create(
                case_id=job.case_id,
                evidence_id=str(recovered_file._id),
                action="HASH_CREATED",
                performed_by=request.user.username,
                notes=f"SHA-256, SHA-512, MD5, SHA-1 hashes created for {recovered_file.filename}.",
                hash_after=final_sha256
            )
            if dest_path.endswith(('.dd', '.img', '.raw', '.e01')):
                ChainOfCustody.create(
                    case_id=job.case_id,
                    evidence_id=str(recovered_file._id),
                    action="IMAGE_CREATED",
                    performed_by=request.user.username,
                    notes=f"Forensic disk image registered: {recovered_file.filename} ({recovered_file.size} bytes).",
                    hash_after=final_sha256
                )
                _log_timeline(
                    case_id=job.case_id,
                    event_type="IMAGE_CREATED",
                    description=f"Forensic image '{recovered_file.filename}' created and registered.",
                    actor=examiner,
                    device_id=device_id,
                    evidence_id=str(recovered_file._id),
                    metadata={"sha256": final_sha256, "size": file_size}
                )
            else:
                _log_timeline(
                    case_id=job.case_id,
                    event_type="FILE_RECOVERED",
                    description=f"File '{recovered_file.filename}' recovered via {recovery_method}.",
                    actor=examiner,
                    device_id=device_id,
                    evidence_id=str(recovered_file._id),
                    metadata={
                        "sha256": final_sha256,
                        "md5": final_md5,
                        "size": file_size,
                        "method": recovery_method
                    }
                )
        except Exception as e:
            print(f"[FileUpload] CoC/Timeline log failure: {e}")

        return Response({
            "success": True,
            "message": "Recovered file saved and logged successfully",
            "file": recovered_file.to_dict()
        })


class RecoveredFilesListView(APIView):
    """
    GET /api/recovery/files/
    Lists recovered files. If case_id query param is provided, filters by case, else lists all.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        if case_id:
            files = RecoveredFile.get_by_case(case_id)
        else:
            files = RecoveredFile.search(limit=500)
        return Response({
            "success": True,
            "count": len(files),
            "files": [f.to_dict() for f in files]
        })



class RecoveredFileDetailView(APIView):
    """
    GET /api/recovery/files/<id>/
    Returns metadata for a single recovered file.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        file_record = RecoveredFile.get_by_id(pk)
        if not file_record:
            return Response({"success": False, "error": "Recovered file not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "file": file_record.to_dict()})


class RecoveredFileSearchView(APIView):
    """
    GET /api/recovery/files/search/
    Search recovered files by filename, extension, hash, case, device, date, size.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = {
            "case_id": request.query_params.get("case_id"),
            "filename": request.query_params.get("filename"),
            "extension": request.query_params.get("extension"),
            "hash_value": request.query_params.get("hash"),
            "device_id": request.query_params.get("device_id"),
            "min_size": request.query_params.get("min_size"),
            "max_size": request.query_params.get("max_size"),
            "keyword": request.query_params.get("keyword"),
            "limit": int(request.query_params.get("limit", 200)),
        }
        files = RecoveredFile.search(**{k: v for k, v in params.items() if v is not None})
        return Response({
            "success": True,
            "count": len(files),
            "files": [f.to_dict() for f in files]
        })


class RecoveredFileHashVerifyView(APIView):
    """
    POST /api/recovery/files/<id>/verify/
    Recomputes SHA256, MD5, SHA1 of the stored binary and compares against DB record.
    Returns verification status: verified / modified / corrupted
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        file_record = RecoveredFile.get_by_id(pk)
        if not file_record:
            return Response({"success": False, "error": "Recovered file not found"}, status=status.HTTP_404_NOT_FOUND)

        file_path = file_record.storage_location
        if not file_path or not os.path.exists(file_path):
            return Response({
                "success": False,
                "error": "File binary not found on server",
                "status": "corrupted"
            }, status=status.HTTP_404_NOT_FOUND)

        # Recompute hashes
        sha256_calc = hashlib.sha256()
        md5_calc = hashlib.md5()
        sha1_calc = hashlib.sha1()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    sha256_calc.update(chunk)
                    md5_calc.update(chunk)
                    sha1_calc.update(chunk)
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Failed to compute hashes: {str(e)}",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        computed_sha256 = sha256_calc.hexdigest()
        computed_md5 = md5_calc.hexdigest()
        computed_sha1 = sha1_calc.hexdigest()

        sha256_match = (computed_sha256 == file_record.hash_sha256) if file_record.hash_sha256 else None
        md5_match = (computed_md5 == file_record.hash_md5) if file_record.hash_md5 else None
        sha1_match = (computed_sha1 == file_record.hash_sha1) if file_record.hash_sha1 else None

        all_match = all(v for v in [sha256_match, md5_match, sha1_match] if v is not None)
        any_mismatch = any(v is False for v in [sha256_match, md5_match, sha1_match])

        if any_mismatch:
            verification_status = "modified"
        elif all_match:
            verification_status = "verified"
        else:
            verification_status = "unverifiable"

        # Log verification
        AuditLog.log(
            user_id=str(request.user._id),
            username=request.user.username,
            action="HASH_VERIFIED",
            resource_type="recovered_file",
            resource_id=str(file_record._id),
            details={
                "filename": file_record.filename,
                "verification_status": verification_status,
                "sha256_match": sha256_match,
                "md5_match": md5_match,
                "sha1_match": sha1_match,
            }
        )
        _log_timeline(
            case_id=file_record.case_id,
            event_type="HASH_VERIFIED",
            description=f"Hash verification for '{file_record.filename}': {verification_status.upper()}",
            actor=request.user.username,
            evidence_id=str(file_record._id),
            metadata={"status": verification_status, "sha256_match": sha256_match}
        )

        return Response({
            "success": True,
            "filename": file_record.filename,
            "verification_status": verification_status,
            "hashes": {
                "sha256": {
                    "stored": file_record.hash_sha256,
                    "computed": computed_sha256,
                    "match": sha256_match,
                },
                "md5": {
                    "stored": file_record.hash_md5,
                    "computed": computed_md5,
                    "match": md5_match,
                },
                "sha1": {
                    "stored": file_record.hash_sha1,
                    "computed": computed_sha1,
                    "match": sha1_match,
                },
            }
        })


class RecoveredFilePreviewView(APIView):
    """
    GET /api/recovery/files/<id>/preview/
    Serves the file binary for in-browser preview with appropriate Content-Type.
    Supports images, PDF, text, JSON, video.
    """
    permission_classes = [IsAuthenticated]

    # Allowed MIME types for preview (blocks dangerous types)
    PREVIEWABLE_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
        'application/pdf',
        'text/plain', 'text/csv', 'text/html', 'text/xml',
        'application/json',
        'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo',
        'audio/mpeg', 'audio/wav',
    }

    def get(self, request, pk):
        file_record = RecoveredFile.get_by_id(pk)
        if not file_record:
            return Response({"success": False, "error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

        file_path = file_record.storage_location
        if not file_path or not os.path.exists(file_path):
            return Response({"success": False, "error": "File binary not found"}, status=status.HTTP_404_NOT_FOUND)

        # Determine MIME type
        mime_type = file_record.mime_type
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Log access
        _log_timeline(
            case_id=file_record.case_id,
            event_type="FILE_PREVIEWED",
            description=f"File '{file_record.filename}' previewed in browser by {request.user.username}.",
            actor=request.user.username,
            evidence_id=str(file_record._id),
        )

        # Stream file
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=mime_type
            )
            # Allow inline display for previewable types
            if mime_type in self.PREVIEWABLE_TYPES:
                response['Content-Disposition'] = f'inline; filename="{file_record.filename}"'
            else:
                response['Content-Disposition'] = f'attachment; filename="{file_record.filename}"'
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecoveredFileDownloadView(APIView):
    """
    GET /api/recovery/files/<id>/download/
    Verify permissions, check case association, verify integrity hash, log, and stream download.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        file_record = RecoveredFile.get_by_id(pk)
        if not file_record:
            return Response({"success": False, "error": "Recovered file not found"}, status=status.HTTP_404_NOT_FOUND)

        # Case access verification
        case = Case.get_by_id(file_record.case_id)
        if not case:
            return Response({"success": False, "error": "Associated case not found"}, status=status.HTTP_404_NOT_FOUND)

        # Gated by investigator/admin permissions
        if request.user.role != 'admin' and str(request.user._id) != str(case.investigator_id) and request.user.username != case.investigator_id:
            assigned = getattr(case, 'assigned_to', [])
            if str(request.user._id) not in assigned and request.user.username not in assigned:
                return Response({"success": False, "error": "Permission denied. You are not assigned to this case."}, status=status.HTTP_403_FORBIDDEN)

        # Verify file path exists
        file_path = file_record.storage_location
        if not file_path or not os.path.exists(file_path):
            return Response({"success": False, "error": "File binary not found on recovery server"}, status=status.HTTP_404_NOT_FOUND)

        # Calculate SHA256 to verify integrity before download
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    sha256.update(chunk)
            calculated_hash = sha256.hexdigest()
        except Exception as e:
            return Response({"success": False, "error": f"Failed to verify file integrity: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if file_record.hash_sha256 and calculated_hash != file_record.hash_sha256:
            return Response({
                "success": False,
                "error": "Integrity check failed: Server file SHA-256 mismatch. Potential tampering detected!"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Log audit trail
        AuditLog.log(
            user_id=str(request.user._id),
            username=request.user.username,
            action="FILE_DOWNLOADED",
            resource_type="recovered_file",
            resource_id=str(file_record._id),
            details={"filename": file_record.filename, "case_id": file_record.case_id}
        )

        # Log CoC Chain event
        ChainOfCustody.create(
            case_id=file_record.case_id,
            evidence_id=str(file_record._id),
            action="FILE_DOWNLOADED",
            performed_by=request.user.username,
            notes=f"File {file_record.filename} downloaded. SHA-256 integrity verified.",
            hash_before=file_record.hash_sha256,
            hash_after=calculated_hash
        )
        _log_timeline(
            case_id=file_record.case_id,
            event_type="FILE_DOWNLOADED",
            description=f"File '{file_record.filename}' downloaded by {request.user.username}. Integrity: verified.",
            actor=request.user.username,
            evidence_id=str(file_record._id),
        )

        # Return streaming file response
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=file_record.filename
        )
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class RecoveryExportView(APIView):
    """
    GET /api/recovery/export/?case_id=<id>
    Exports a ZIP package containing all recovered files, hashes, timeline, and metadata.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        if not case_id:
            return Response({"success": False, "error": "case_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        case = Case.get_by_id(case_id)
        if not case:
            return Response({"success": False, "error": "Case not found"}, status=status.HTTP_404_NOT_FOUND)

        files = RecoveredFile.get_by_case(case_id)
        timeline = TimelineEvent.get_by_case(case_id)

        # Build ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add recovered files
            for rf in files:
                if rf.storage_location and os.path.exists(rf.storage_location):
                    zf.write(rf.storage_location, f"RecoveredFiles/{rf.filename}")

            # Add hashes CSV
            hash_rows = [["Filename", "SHA256", "MD5", "SHA1", "Size", "RecoveryMethod", "OriginalPath"]]
            for rf in files:
                hash_rows.append([
                    rf.filename, rf.hash_sha256 or "", rf.hash_md5 or "",
                    rf.hash_sha1 or "", str(rf.size),
                    rf.recovery_method or "", rf.original_path or ""
                ])
            hash_csv = io.StringIO()
            writer = csv.writer(hash_csv)
            writer.writerows(hash_rows)
            zf.writestr("Hashes/file_hashes.csv", hash_csv.getvalue())

            # Add metadata JSON
            import json
            metadata = {
                "case_id": case_id,
                "case_number": case.case_number,
                "title": case.title,
                "export_time": datetime.now(timezone.utc).isoformat(),
                "total_files": len(files),
                "files": [f.to_dict() for f in files]
            }
            zf.writestr("Metadata/metadata.json", json.dumps(metadata, indent=2, default=str))

            # Add timeline CSV
            timeline_rows = [["Timestamp", "EventType", "Description", "Actor", "DeviceID", "EvidenceID"]]
            for ev in timeline:
                timeline_rows.append([
                    ev.timestamp.isoformat() if ev.timestamp else "",
                    ev.event_type or "", ev.description or "",
                    ev.actor or "", ev.device_id or "", ev.evidence_id or ""
                ])
            timeline_csv = io.StringIO()
            t_writer = csv.writer(timeline_csv)
            t_writer.writerows(timeline_rows)
            zf.writestr("Timeline/timeline.csv", timeline_csv.getvalue())

        zip_buffer.seek(0)

        # Log
        AuditLog.log(
            user_id=str(request.user._id),
            username=request.user.username,
            action="CASE_EXPORTED",
            resource_type="case",
            resource_id=case_id,
            details={"file_count": len(files)}
        )
        _log_timeline(
            case_id=case_id,
            event_type="CASE_EXPORTED",
            description=f"ZIP export of case {case.case_number} by {request.user.username}. {len(files)} files.",
            actor=request.user.username,
        )

        response = StreamingHttpResponse(
            zip_buffer,
            content_type='application/zip'
        )
        safe_case_num = sanitize_filename(case.case_number)
        response['Content-Disposition'] = f'attachment; filename="AIDFIRS_{safe_case_num}_Export.zip"'
        return response


class TimelineView(APIView):
    """
    GET /api/recovery/timeline/?case_id=<id>
    POST /api/recovery/timeline/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        if not case_id:
            return Response({"success": False, "error": "case_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        event_type = request.query_params.get("event_type")
        events = TimelineEvent.get_by_case(case_id, event_type=event_type)
        return Response({
            "success": True,
            "count": len(events),
            "events": [e.to_dict() for e in events]
        })

    def post(self, request):
        case_id = request.data.get("case_id")
        event_type = request.data.get("event_type")
        description = request.data.get("description")
        if not case_id or not event_type or not description:
            return Response({"success": False, "error": "case_id, event_type, description required"}, status=status.HTTP_400_BAD_REQUEST)
        event = TimelineEvent.create(
            case_id=case_id,
            event_type=event_type,
            description=description,
            actor=request.data.get("actor", request.user.username),
            device_id=request.data.get("device_id"),
            evidence_id=request.data.get("evidence_id"),
            metadata=request.data.get("metadata", {})
        )
        return Response({"success": True, "event": event.to_dict()}, status=status.HTTP_201_CREATED)


class TimelineExportView(APIView):
    """
    GET /api/recovery/timeline/export/?case_id=<id>
    Exports timeline as CSV.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        if not case_id:
            return Response({"success": False, "error": "case_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        events = TimelineEvent.get_by_case(case_id)

        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Timestamp", "EventType", "Description", "Actor", "DeviceID", "EvidenceID", "Metadata"])
        for ev in events:
            writer.writerow([
                ev.timestamp.isoformat() if ev.timestamp else "",
                ev.event_type or "",
                ev.description or "",
                ev.actor or "",
                ev.device_id or "",
                ev.evidence_id or "",
                str(ev.metadata) if ev.metadata else ""
            ])

        response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="AIDFIRS_Timeline_{case_id}.csv"'
        return response


class ChainOfCustodyExportView(APIView):
    """
    GET /api/recovery/coc/export/?case_id=<id>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        if not case_id:
            return Response({"success": False, "error": "case_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            coc_entries = ChainOfCustody.get_by_case(case_id)
        except Exception:
            coc_entries = []

        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Timestamp", "Action", "PerformedBy", "EvidenceID", "Notes", "HashBefore", "HashAfter"])
        for entry in coc_entries:
            d = entry.to_dict() if hasattr(entry, 'to_dict') else entry
            writer.writerow([
                d.get("timestamp", ""), d.get("action", ""), d.get("performed_by", ""),
                d.get("evidence_id", ""), d.get("notes", ""),
                d.get("hash_before", ""), d.get("hash_after", "")
            ])

        response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="AIDFIRS_ChainOfCustody_{case_id}.csv"'
        return response
