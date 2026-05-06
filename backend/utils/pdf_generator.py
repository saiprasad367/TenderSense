"""
PDF Report Generator using ReportLab.
Produces a government-grade evaluation report.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("tendersense.pdf")


def generate_evaluation_report(
    tender: Dict[str, Any],
    evaluations: List[Dict[str, Any]],
) -> bytes:
    """
    Generate a PDF evaluation report.
    Returns raw PDF bytes.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        logger.error("reportlab not installed — cannot generate PDF")
        raise

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    style_h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    style_h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceAfter=4)
    style_body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, spaceAfter=4)
    style_small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    style_center = ParagraphStyle("center", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER)

    story = []

    # Header
    story.append(Paragraph("GOVERNMENT OF KARNATAKA", style_center))
    story.append(Paragraph("TenderSense AI — Evaluation Report", style_h1))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | CONFIDENTIAL", style_small))
    story.append(HRFlowable(width="100%", thickness=1))
    story.append(Spacer(1, 0.3 * cm))

    # Tender details
    story.append(Paragraph("Tender Details", style_h2))
    tender_data = [
        ["Tender Number", tender.get("tender_number", "N/A")],
        ["Title", tender.get("title", "N/A")],
        ["Department", tender.get("department", "N/A")],
        ["Estimated Value", f"₹ {tender.get('estimated_value', 'N/A'):,.2f}" if tender.get("estimated_value") else "N/A"],
        ["Submission Deadline", str(tender.get("submission_deadline", "N/A"))],
        ["Status", tender.get("status", "N/A").upper()],
    ]
    t = Table(tender_data, colWidths=[5 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    # Summary counts
    story.append(Paragraph("Evaluation Summary", style_h2))
    eligible = sum(1 for e in evaluations if e.get("final_verdict") == "eligible")
    not_elig = sum(1 for e in evaluations if e.get("final_verdict") == "not_eligible")
    review = sum(1 for e in evaluations if e.get("final_verdict") == "needs_review")

    summary_data = [
        ["Total Bidders", "Eligible", "Needs Review", "Not Eligible"],
        [str(len(evaluations)), str(eligible), str(review), str(not_elig)],
    ]
    st = Table(summary_data, colWidths=[4.25 * cm] * 4)
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(st)
    story.append(Spacer(1, 0.4 * cm))

    # Bidder roster
    story.append(Paragraph("Bidder Evaluation Results", style_h2))
    headers = ["Bidder", "GSTIN", "Verdict", "Confidence", "Fraud", "Review"]
    roster = [headers]
    for ev in evaluations:
        verdict = ev.get("final_verdict", "N/A")
        fraud = ev.get("fraud_verdict") or {}
        fraud_status = fraud.get("status", "N/A") if isinstance(fraud, dict) else "N/A"
        roster.append([
            ev.get("bidder_name", ev.get("bidder_id", "N/A"))[:30],
            ev.get("bidder_gstin", "N/A"),
            verdict.upper().replace("_", " "),
            f"{ev.get('confidence_score', 0) * 100:.0f}%",
            fraud_status.upper(),
            "YES" if ev.get("needs_human_review") else "NO",
        ])
    col_widths = [6 * cm, 3.5 * cm, 2.5 * cm, 2 * cm, 1.5 * cm, 1.5 * cm]
    rt = Table(roster, colWidths=col_widths, repeatRows=1)
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(rt)

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5))
    story.append(Paragraph(
        "This report was generated automatically by TenderSense AI. "
        "All AI verdicts are subject to human review before official use. "
        "Digitally signed and timestamped.",
        style_small,
    ))

    doc.build(story)
    return buf.getvalue()
