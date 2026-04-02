import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def generate_evidence_pdf(evidence):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Title
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    elements.append(Paragraph(f"Evidence Report: {evidence.file_name}", title_style))
    elements.append(Spacer(1, 20))
    
    # Details table
    data = [
        ["Property", "Value"],
        ["Case ID", str(evidence.case_id)],
        ["Evidence Type", evidence.evidence_type.replace('_', ' ').title()],
        ["File Name", evidence.file_name],
        ["File Size", f"{evidence.file_size} bytes"],
        ["Status", evidence.status.title()],
    ]
    
    if hasattr(evidence, 'collected_at') and evidence.collected_at:
        try:
            date_str = evidence.collected_at.strftime("%Y-%m-%d %H:%M:%S %Z")
        except:
            date_str = str(evidence.collected_at)
        data.append(["Collected At", date_str])
        
    if hasattr(evidence, 'hash_md5') and evidence.hash_md5:
        data.append(["MD5 Hash", evidence.hash_md5])
    if hasattr(evidence, 'hash_sha256') and evidence.hash_sha256:
        # reportlab has issue with very long strings without spaces in tables, wrap it or use smaller font
        # For a standard SHA256, it might warp the flow. Paragraph is safer inside table.
        hash_para = Paragraph(evidence.hash_sha256, styles['Normal'])
        data.append(["SHA256 Hash", hash_para])
        
    table = Table(data, colWidths=[120, 350])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Description
    elements.append(Paragraph("Description:", styles['Heading2']))
    desc_text = evidence.description if hasattr(evidence, 'description') and evidence.description else "No description provided."
    elements.append(Paragraph(desc_text, styles['Normal']))
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()
