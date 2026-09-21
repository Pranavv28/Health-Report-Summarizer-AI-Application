import io
import json
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from schema import HealthReportAnalysis


def generate_json_export(analysis: HealthReportAnalysis) -> str:
    """
    Generate a structured JSON string from a HealthReportAnalysis instance.

    Args:
        analysis: Parsed health report analysis model.

    Returns:
        Pretty-printed JSON string of the analysis.
    """
    return analysis.model_dump_json(indent=2)


def generate_json_dict(analysis: HealthReportAnalysis) -> dict[str, Any]:
    """
    Generate a dictionary from a HealthReportAnalysis instance.

    Args:
        analysis: Parsed health report analysis model.

    Returns:
        Dictionary representation of the analysis.
    """
    return analysis.model_dump()


def generate_pdf_report(analysis: HealthReportAnalysis, pagesize=letter) -> bytes:
    """Generate a downloadable PDF bytes buffer from a HealthReportAnalysis instance.
    
    Optimized for multi-device compatibility (Mobile PDF Readers, Tablets, Desktops, and Print).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom responsive typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=14
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=5
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )

    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#991B1B'),
        spaceBefore=6,
        spaceAfter=12
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph(analysis.report_title or "Health Diagnostic Summary", title_style))
    story.append(Paragraph("AI-Assisted Health Report Summary | Educational Reference Only", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

    # Medical Disclaimer Notice
    disclaimer_box = Paragraph(
        "<b>Medical Disclaimer:</b> This document is an AI-generated summary intended strictly for educational and informational purposes. "
        "It is not a substitute for professional medical advice, diagnosis, or treatment.",
        disclaimer_style
    )
    story.append(disclaimer_box)

    # Executive Summary
    story.append(Paragraph("Executive Patient Summary", section_heading))
    story.append(Paragraph(analysis.patient_summary or "No summary available.", body_style))
    story.append(Spacer(1, 10))

    # Biomarkers Table (Formatted to fit Letter & A4 and mobile PDF screens perfectly)
    if analysis.biomarkers:
        story.append(Paragraph("Extracted Test Biomarkers & Lab Results", section_heading))
        
        table_data = [
            [
                Paragraph("<b>Test Parameter</b>", table_header_style),
                Paragraph("<b>Result</b>", table_header_style),
                Paragraph("<b>Unit</b>", table_header_style),
                Paragraph("<b>Reference Range</b>", table_header_style),
                Paragraph("<b>Status</b>", table_header_style)
            ]
        ]

        for b in analysis.biomarkers:
            status_color = "#16A34A"  # Normal Green
            if b.status.lower() in ["high", "elevated"]:
                status_color = "#D97706"  # High Orange
            elif b.status.lower() in ["low", "decreased"]:
                status_color = "#2563EB"  # Low Blue
            elif b.status.lower() in ["critical", "abnormal"]:
                status_color = "#DC2626"  # Critical Red

            status_p = Paragraph(f"<font color='{status_color}'><b>{b.status}</b></font>", table_body_style)
            
            table_data.append([
                Paragraph(b.parameter_name, table_body_style),
                Paragraph(b.value, table_body_style),
                Paragraph(b.unit or "-", table_body_style),
                Paragraph(b.reference_range or "-", table_body_style),
                status_p
            ])

        # Column widths totaling 520pt (Fits both Letter 540pt and A4 523pt printable width)
        t = Table(table_data, colWidths=[140, 75, 70, 135, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

    # Key Findings & Abnormal Alerts
    if analysis.key_findings:
        story.append(Paragraph("Key Findings & Abnormal Alerts", section_heading))
        for item in analysis.key_findings:
            story.append(Paragraph(f"• {item}", body_style))
        story.append(Spacer(1, 10))

    # Questions for Doctor
    if analysis.questions_for_doctor:
        story.append(Paragraph("Recommended Questions for Your Doctor", section_heading))
        for q in analysis.questions_for_doctor:
            story.append(Paragraph(f"☐ {q}", body_style))
        story.append(Spacer(1, 10))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
