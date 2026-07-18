import os
import hashlib
from datetime import datetime, timezone
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from .models import RecoveryJob, RecoveredFile
from .serializers import RecoveryJobSerializer, RecoveredFileSerializer
from devices.models import Device
from cases.models import Case
from cases.coc_models import ChainOfCustody
from accounts.models import AuditLog

# Storage root for uploaded files
STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage', 'recoveries')

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
            notes=f"Recovery job started for device {device.device_name}."
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


class RecoveryJobDetailView(APIView):
    """
    PATCH /api/recovery/jobs/<id>/
    Updates a recovery job status, progress, files_found, etc.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        job = RecoveryJob.get_by_id(pk)
        if not job:
            return Response({"success": False, "error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        # Allowed fields
        status_val = request.data.get("status")
        progress = request.data.get("progress")
        files_found = request.data.get("files_found")

        updates = {}
        if status_val:
            updates["status"] = status_val
            if status_val in ("COMPLETED", "FAILED"):
                updates["completion_time"] = datetime.now(timezone.utc)
        if progress is not None:
            updates["progress"] = int(progress)
        if files_found is not None:
            updates["files_found"] = int(files_found)

        job.update(**updates)

        return Response({
            "success": True,
            "job": job.to_dict()
        })


class RecoveredFileUploadView(APIView):
    """
    POST /api/recovery/jobs/<id>/upload/
    Uploads a carved/recovered file binary and registers it.
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
        filename = request.data.get("filename", uploaded_file.name).strip()

        # Save to filesystem
        os.makedirs(STORAGE_ROOT, exist_ok=True)
        job_dir = os.path.join(STORAGE_ROOT, str(job._id))
        os.makedirs(job_dir, exist_ok=True)
        
        # Clean path injection attempts
        safe_filename = os.path.basename(filename)
        dest_path = os.path.join(job_dir, safe_filename)

        # Handle duplicate filenames
        counter = 1
        base, ext = os.path.splitext(dest_path)
        while os.path.exists(dest_path):
            dest_path = f"{base}_{counter}{ext}"
            counter += 1
        
        # Calculate SHA256 / SHA512 locally if not provided
        sha256_calc = hashlib.sha256()
        sha512_calc = hashlib.sha512()
        
        try:
            with open(dest_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
                    sha256_calc.update(chunk)
                    sha512_calc.update(chunk)
        except Exception as e:
            return Response({"success": False, "error": f"Failed to save file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        final_sha256 = hash_sha256 or sha256_calc.hexdigest()
        final_sha512 = hash_sha512 or sha512_calc.hexdigest()
        file_size = os.path.getsize(dest_path)

        # Create model in MongoDB
        recovered_file = RecoveredFile.create(
            filename=os.path.basename(dest_path),
            storage_location=dest_path,
            hash_sha256=final_sha256,
            hash_sha512=final_sha512,
            size=file_size,
            case_id=job.case_id,
            recovery_job_id=str(job._id)
        )

        # Log CoC events
        try:
            ChainOfCustody.create(
                case_id=job.case_id,
                evidence_id=job.device_id,
                action="FILE_RECOVERED",
                performed_by=request.user.username,
                notes=f"File recovered: {recovered_file.filename} (Size: {recovered_file.size} bytes).",
                hash_after=final_sha256
            )
            ChainOfCustody.create(
                case_id=job.case_id,
                evidence_id=str(recovered_file._id),
                action="HASH_CREATED",
                performed_by=request.user.username,
                notes=f"SHA-256 and SHA-512 hashes created for recovered file {recovered_file.filename}.",
                hash_after=final_sha256
            )
            if dest_path.endswith(('.dd', '.img', '.raw')):
                ChainOfCustody.create(
                    case_id=job.case_id,
                    evidence_id=str(recovered_file._id),
                    action="IMAGE_CREATED",
                    performed_by=request.user.username,
                    notes=f"Forensic disk image created: {recovered_file.filename} (Size: {recovered_file.size} bytes).",
                    hash_after=final_sha256
                )
        except Exception as e:
            print(f"[FileUpload] CoC Log failure: {e}")

        return Response({
            "success": True,
            "message": "Recovered file saved and logged successfully",
            "file": recovered_file.to_dict()
        })


class RecoveredFilesListView(APIView):
    """
    GET /api/recovery/files/
    Query parameters: case_id
    Lists all recovered files for a case.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        if not case_id:
            return Response({"success": False, "error": "case_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        files = RecoveredFile.get_by_case(case_id)
        return Response({
            "success": True,
            "files": [f.to_dict() for f in files]
        })


class RecoveredFileDownloadView(APIView):
    """
    GET /api/recovery/files/<id>/download/
    Verify permissions, check case association, check integrity hash, log, and download.
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
        if not os.path.exists(file_path):
            return Response({"success": False, "error": "File binary not found on recovery server"}, status=status.HTTP_404_NOT_FOUND)

        # Calculate SHA256 of the binary to verify integrity
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    sha256.update(chunk)
            calculated_hash = sha256.hexdigest()
        except Exception as e:
            return Response({"success": False, "error": f"Failed to verify file integrity: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if calculated_hash != file_record.hash_sha256:
            return Response({
                "success": False,
                "error": "Integrity check failed: Server file SHA-256 mismatch with DB record. Potential tampering detected!"
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
            notes=f"File {file_record.filename} downloaded by {request.user.username}. Integrity verified: SHA-256 match.",
            hash_before=file_record.hash_sha256,
            hash_after=calculated_hash
        )

        # Return file response
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_record.filename)
        return response
