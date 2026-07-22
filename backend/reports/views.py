import os
import threading
import mimetypes
from datetime import datetime, timezone
from django.http import FileResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Report
from .generator import generate_html_report, generate_pdf_report, generate_docx_report
from cases.models import Case
from cases.coc_models import ChainOfCustody
from recovery.models import RecoveredFile, TimelineEvent
from accounts.models import AuditLog


def _generate_report_async(report, case, files, timeline, coc_entries, examiner):
    """Run report generation in background thread."""
    report.update(status="generating")
    try:
        fmt = report.format
        report_id = str(report._id)

        if fmt == 'html':
            html_content = generate_html_report(case, files, timeline, coc_entries, examiner)
            from reports.generator import REPORTS_STORAGE
            filename = f"AIDFIRS_Report_{report_id}.html"
            output_path = os.path.join(REPORTS_STORAGE, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        elif fmt == 'pdf':
            output_path = generate_pdf_report(case, files, timeline, coc_entries, examiner, report_id)
        elif fmt == 'docx':
            output_path = generate_docx_report(case, files, timeline, coc_entries, examiner, report_id)
        else:
            report.update(status="failed")
            return

        report.update(status="completed", file_path=output_path)
        print(f"[Reports] Report {report_id} generated: {output_path}")
    except Exception as e:
        print(f"[Reports] Report generation failed: {e}")
        report.update(status="failed")


class ReportGenerateView(APIView):
    """
    POST /api/reports/generate/
    Generate a forensic report for a case in specified format.
    Returns immediately with report ID; generation runs in background.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        case_id = request.data.get("case_id")
        report_format = request.data.get("format", "pdf").lower()
        report_type = request.data.get("report_type", "full")
        title = request.data.get("title")

        if not case_id:
            return Response({"success": False, "error": "case_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if report_format not in ('pdf', 'docx', 'html'):
            return Response({"success": False, "error": "format must be pdf, docx, or html"}, status=status.HTTP_400_BAD_REQUEST)

        case = Case.get_by_id(case_id)
        if not case:
            return Response({"success": False, "error": "Case not found"}, status=status.HTTP_404_NOT_FOUND)

        # Create report record
        examiner = request.user.username
        report = Report.create(
            case_id=case_id,
            report_type=report_type,
            format=report_format,
            examiner=examiner,
            title=title or f"Forensic Report - {case.case_number} - {report_type.capitalize()}"
        )

        # Gather data
        files = RecoveredFile.get_by_case(case_id)
        timeline = TimelineEvent.get_by_case(case_id)
        try:
            coc_entries = ChainOfCustody.get_by_case(case_id)
        except Exception:
            coc_entries = []

        # Launch generation in background thread
        t = threading.Thread(
            target=_generate_report_async,
            args=(report, case, files, timeline, coc_entries, examiner),
            daemon=True
        )
        t.start()

        # Log audit
        AuditLog.log(
            user_id=str(request.user._id),
            username=request.user.username,
            action="REPORT_GENERATED",
            resource_type="report",
            resource_id=str(report._id),
            details={"case_id": case_id, "format": report_format, "type": report_type}
        )

        return Response({
            "success": True,
            "message": f"Report generation started. Poll /api/reports/{report._id}/ for status.",
            "report": report.to_dict()
        }, status=status.HTTP_202_ACCEPTED)


class ReportListView(APIView):
    """
    GET /api/reports/?case_id=<id>
    List all reports for a case.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        case_id = request.query_params.get("case_id")
        if not case_id:
            return Response({"success": False, "error": "case_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        reports = Report.get_by_case(case_id)
        return Response({
            "success": True,
            "count": len(reports),
            "reports": [r.to_dict() for r in reports]
        })


class ReportDetailView(APIView):
    """
    GET /api/reports/<id>/
    Poll report status.
    DELETE /api/reports/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        report = Report.get_by_id(pk)
        if not report:
            return Response({"success": False, "error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "report": report.to_dict()})

    def delete(self, request, pk):
        report = Report.get_by_id(pk)
        if not report:
            return Response({"success": False, "error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        report.delete()
        return Response({"success": True, "message": "Report deleted"})


class ReportDownloadView(APIView):
    """
    GET /api/reports/<id>/download/?format=<pdf|docx|html>
    Download the generated report file.
    """
    permission_classes = [IsAuthenticated]

    MIME_TYPES = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'html': 'text/html',
    }

    def get(self, request, pk):
        report = Report.get_by_id(pk)
        if not report:
            return Response({"success": False, "error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

        if report.status != "completed":
            return Response({
                "success": False,
                "error": f"Report is not ready yet. Status: {report.status}",
                "status": report.status
            }, status=status.HTTP_400_BAD_REQUEST)

        file_path = report.file_path
        if not file_path or not os.path.exists(file_path):
            return Response({"success": False, "error": "Report file not found on server"}, status=status.HTTP_404_NOT_FOUND)

        mime_type = self.MIME_TYPES.get(report.format, 'application/octet-stream')
        filename = os.path.basename(file_path)

        AuditLog.log(
            user_id=str(request.user._id),
            username=request.user.username,
            action="REPORT_DOWNLOADED",
            resource_type="report",
            resource_id=str(report._id),
            details={"format": report.format, "case_id": report.case_id}
        )

        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=filename,
            content_type=mime_type
        )
