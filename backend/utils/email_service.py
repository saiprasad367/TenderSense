"""
Email Notification Service — TenderSense AI
Sends Karnataka Government-styled evaluation result emails to bidders.
Attaches a detailed PDF rejection report if verdict is not_eligible or needs_review.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import smtplib
import textwrap
from datetime import datetime
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("tendersense.email_service")

# ─── SMTP Config (loaded from .env) ─────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TenderSense AI — Government of Karnataka")


# ─── Verdict Colours ─────────────────────────────────────────────────────────
_VERDICT_COLOUR = {
    "eligible": "#16a34a",
    "not_eligible": "#dc2626",
    "needs_review": "#d97706",
}
_VERDICT_LABEL = {
    "eligible": "✅ ELIGIBLE",
    "not_eligible": "❌ NOT ELIGIBLE",
    "needs_review": "⚠️ UNDER REVIEW",
}
_VERDICT_BADGE_BG = {
    "eligible": "#dcfce7",
    "not_eligible": "#fee2e2",
    "needs_review": "#fef3c7",
}


# ─── HTML Email Template ─────────────────────────────────────────────────────
def _build_html_email(
    company_name: str,
    tender_title: str,
    tender_number: str,
    verdict: str,
    confidence: float,
    explanation: str,
    evaluation_id: str,
    red_flags: list,
) -> str:
    verdict_color = _VERDICT_COLOUR.get(verdict, "#6b7280")
    verdict_label = _VERDICT_LABEL.get(verdict, verdict.upper())
    badge_bg = _VERDICT_BADGE_BG.get(verdict, "#f3f4f6")
    now = datetime.now().strftime("%d %B %Y, %I:%M %p IST")
    confidence_pct = round(confidence * 100, 1)

    flags_html = ""
    if red_flags:
        flags_html = "<ul style='margin:8px 0;padding-left:20px;'>"
        for flag in red_flags[:5]:
            flags_html += f"<li style='color:#dc2626;margin-bottom:4px;font-size:13px;'>{flag}</li>"
        flags_html += "</ul>"
    else:
        flags_html = "<p style='color:#16a34a;font-size:13px;'>No fraud indicators detected.</p>"

    note_section = ""
    if verdict == "not_eligible":
        note_section = """
        <div style="margin:24px 0;padding:16px;background:#fef2f2;border-left:4px solid #dc2626;border-radius:4px;">
          <p style="margin:0;font-weight:600;color:#dc2626;">Important Notice</p>
          <p style="margin:8px 0 0;color:#374151;font-size:13px;">
            A detailed PDF rejection report is attached to this email. It contains the specific
            criteria that were not met, the extracted evidence, and the AI's reasoning chain.
            You may use this document for any formal appeal or RTI query.
          </p>
        </div>"""
    elif verdict == "needs_review":
        note_section = """
        <div style="margin:24px 0;padding:16px;background:#fffbeb;border-left:4px solid #d97706;border-radius:4px;">
          <p style="margin:0;font-weight:600;color:#d97706;">Pending Human Review</p>
          <p style="margin:8px 0 0;color:#374151;font-size:13px;">
            Your application has been flagged for manual review by a Senior Evaluation Officer.
            You will receive a final decision within 5 working days. A detailed report is attached.
          </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>TenderSense AI — Evaluation Result</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

  <!-- HEADER -->
  <tr><td style="background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);padding:32px;border-radius:12px 12px 0 0;text-align:center;">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Karnataka_Rajya_Sarkar_seal.png/200px-Karnataka_Rajya_Sarkar_seal.png"
         alt="Karnataka Seal" width="60" height="60"
         style="border-radius:50%;background:white;padding:4px;margin-bottom:12px;display:block;margin-left:auto;margin-right:auto;" />
    <p style="margin:0;color:#93c5fd;font-size:11px;letter-spacing:2px;text-transform:uppercase;">Government of Karnataka</p>
    <h1 style="margin:6px 0 0;color:white;font-size:22px;font-weight:700;">e-Procurement Evaluation Result</h1>
    <p style="margin:6px 0 0;color:#bfdbfe;font-size:13px;">Powered by TenderSense AI · {now}</p>
  </td></tr>

  <!-- BODY -->
  <tr><td style="background:white;padding:32px;">

    <p style="margin:0 0 8px;color:#6b7280;font-size:13px;">Dear Applicant,</p>
    <p style="margin:0 0 24px;color:#111827;font-size:15px;">
      The AI evaluation of your bid submission for the tender listed below has been completed.
      Your result is provided below.
    </p>

    <!-- TENDER INFO -->
    <table width="100%" cellpadding="12" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:24px;">
      <tr>
        <td style="border-bottom:1px solid #e2e8f0;">
          <p style="margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Company Name</p>
          <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#111827;">{company_name}</p>
        </td>
      </tr>
      <tr>
        <td style="border-bottom:1px solid #e2e8f0;">
          <p style="margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Tender</p>
          <p style="margin:4px 0 0;font-size:14px;color:#111827;">{tender_title}</p>
        </td>
      </tr>
      <tr>
        <td>
          <p style="margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Tender Number</p>
          <p style="margin:4px 0 0;font-size:13px;color:#374151;font-family:monospace;">{tender_number}</p>
        </td>
      </tr>
    </table>

    <!-- VERDICT BADGE -->
    <div style="text-align:center;margin:24px 0;padding:28px;background:{badge_bg};border:2px solid {verdict_color};border-radius:12px;">
      <p style="margin:0 0 8px;font-size:13px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">AI Evaluation Verdict</p>
      <p style="margin:0;font-size:32px;font-weight:800;color:{verdict_color};">{verdict_label}</p>
      <p style="margin:8px 0 0;font-size:14px;color:{verdict_color};opacity:0.8;">
        AI Confidence Score: <strong>{confidence_pct}%</strong>
      </p>
    </div>

    <!-- SUMMARY -->
    <h3 style="margin:24px 0 8px;font-size:15px;color:#111827;border-left:3px solid #2563eb;padding-left:10px;">
      Evaluation Summary
    </h3>
    <p style="margin:0 0 16px;color:#374151;font-size:14px;line-height:1.6;">
      {explanation}
    </p>

    <!-- FLAGS -->
    <h3 style="margin:20px 0 8px;font-size:15px;color:#111827;border-left:3px solid #dc2626;padding-left:10px;">
      Risk Indicators
    </h3>
    {flags_html}

    {note_section}

    <!-- EVALUATION ID -->
    <div style="margin:24px 0 0;padding:12px 16px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0;">
      <p style="margin:0;font-size:11px;color:#6b7280;">Evaluation Reference ID</p>
      <p style="margin:4px 0 0;font-size:12px;color:#374151;font-family:monospace;">{evaluation_id}</p>
      <p style="margin:8px 0 0;font-size:11px;color:#9ca3af;">
        Quote this ID in any RTI query or formal appeal. This evaluation is legally admissible
        under the Karnataka Transparency in Public Procurement Act, 1999.
      </p>
    </div>

  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#1e3a5f;padding:20px 32px;border-radius:0 0 12px 12px;text-align:center;">
    <p style="margin:0;color:#93c5fd;font-size:12px;">
      This is an automated message from TenderSense AI, an e-Governance initiative of the Government of Karnataka.
    </p>
    <p style="margin:6px 0 0;color:#60a5fa;font-size:11px;">
      Do not reply to this email. For queries, contact your department's procurement officer.
    </p>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


# ─── PDF Report Generator ────────────────────────────────────────────────────
def _build_rejection_pdf(
    company_name: str,
    tender_title: str,
    tender_number: str,
    verdict: str,
    confidence: float,
    evaluation_id: str,
    finance: dict,
    tech: dict,
    compliance: dict,
    validation: dict,
    fraud: dict,
    explanation: dict,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Styles
    title_style = ParagraphStyle("Title", parent=styles["Normal"], fontSize=16, fontName="Helvetica-Bold", textColor=colors.HexColor("#1e3a5f"), spaceAfter=6, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#6b7280"), spaceAfter=4, alignment=TA_CENTER)
    section_style = ParagraphStyle("Sec", parent=styles["Normal"], fontSize=12, fontName="Helvetica-Bold", textColor=colors.HexColor("#1e3a5f"), spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#374151"), spaceAfter=4, leading=15)
    red_style = ParagraphStyle("Red", parent=body_style, textColor=colors.HexColor("#dc2626"))
    green_style = ParagraphStyle("Green", parent=body_style, textColor=colors.HexColor("#16a34a"))
    amber_style = ParagraphStyle("Amber", parent=body_style, textColor=colors.HexColor("#d97706"))

    # Header
    story.append(Paragraph("GOVERNMENT OF KARNATAKA", title_style))
    story.append(Paragraph("e-Procurement Evaluation Report — TenderSense AI", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb")))
    story.append(Spacer(1, 0.3 * cm))

    # Metadata Table
    meta_data = [
        ["Company Name:", company_name],
        ["Tender Title:", tender_title],
        ["Tender Number:", tender_number],
        ["Evaluation ID:", evaluation_id],
        ["Report Generated:", datetime.now().strftime("%d %B %Y, %I:%M %p IST")],
        ["AI Confidence Score:", f"{round(confidence * 100, 1)}%"],
    ]
    meta_table = Table(meta_data, colWidths=[4.5 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7280")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4 * cm))

    # Verdict Banner
    verdict_label = _VERDICT_LABEL.get(verdict, verdict.upper()).replace("✅", "").replace("❌", "").replace("⚠️", "").strip()
    verdict_color_hex = _VERDICT_COLOUR.get(verdict, "#6b7280")
    verdict_data = [[f"FINAL VERDICT: {verdict_label}"]]
    verdict_table = Table(verdict_data, colWidths=[16.5 * cm])
    verdict_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(verdict_color_hex)),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 14),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [5]),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 0.5 * cm))

    # Summary
    summary_text = ""
    if isinstance(explanation, dict):
        summary_text = explanation.get("summary", "") or explanation.get("recommendation", "")
    if not summary_text:
        summary_text = "See detailed agent analysis below."
    story.append(Paragraph("Evaluation Summary", section_style))
    story.append(Paragraph(summary_text[:600], body_style))

    # Agent Results
    def _agent_section(title: str, result: dict, weight: str):
        status = result.get("status", "unknown")
        colour = green_style if status == "pass" else (red_style if status == "fail" else amber_style)
        story.append(Paragraph(f"{title} [{weight}]", section_style))
        story.append(Paragraph(f"Status: {status.upper()} | Confidence: {round(result.get('confidence', 0) * 100)}%", colour))
        reasoning = result.get("agent_reasoning", "No reasoning captured.")
        story.append(Paragraph(str(reasoning)[:500], body_style))

        criteria = result.get("criteria_results", [])
        if criteria:
            crit_data = [["Criterion", "Result", "Extracted", "Required"]]
            for c in criteria[:8]:
                crit_data.append([
                    str(c.get("criterion_id", ""))[:20],
                    str(c.get("result", "")).upper(),
                    str(c.get("extracted_value", ""))[:30],
                    str(c.get("required_value", ""))[:30],
                ])
            crit_table = Table(crit_data, colWidths=[3 * cm, 2.5 * cm, 5.5 * cm, 5.5 * cm])
            crit_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(crit_table)
        story.append(Spacer(1, 0.2 * cm))

    _agent_section("💰 Financial Evaluation", finance, "30%")
    _agent_section("🏗️ Technical Evaluation", tech, "30%")
    _agent_section("📋 Compliance Evaluation", compliance, "20%")
    _agent_section("📁 Document Validation", validation, "10%")

    # Fraud Section
    story.append(Paragraph("🚨 Fraud & Risk Analysis [10%]", section_style))
    risk_score = fraud.get("risk_score", 0)
    fraud_colour = green_style if risk_score < 30 else (amber_style if risk_score < 70 else red_style)
    story.append(Paragraph(f"Risk Score: {risk_score}/100", fraud_colour))
    indicators = fraud.get("fraud_indicators", [])
    if indicators:
        for ind in indicators[:5]:
            sev = ind.get("severity", "medium")
            ind_colour = red_style if sev == "high" else amber_style
            story.append(Paragraph(f"• [{sev.upper()}] {ind.get('description', '')}", ind_colour))
    else:
        story.append(Paragraph("• No fraud indicators detected.", green_style))

    # Legal Footer
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.2 * cm))
    legal_text = (
        f"This report was generated automatically by TenderSense AI on {datetime.now().strftime('%d %B %Y')}. "
        "It is legally admissible as an evaluation record under the Karnataka Transparency in Public Procurement Act, 1999. "
        f"For appeals, quote Evaluation Reference ID: {evaluation_id}. "
        "Verdicts are based on documents submitted by the bidder and live data from Government of India API services."
    )
    story.append(Paragraph(legal_text, ParagraphStyle("Legal", parent=body_style, fontSize=8, textColor=colors.HexColor("#9ca3af"), alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ─── Main Email Sender ────────────────────────────────────────────────────────
async def send_evaluation_result(
    bidder_email: str,
    company_name: str,
    tender_title: str,
    tender_number: str,
    verdict: str,
    confidence: float,
    evaluation_id: str,
    finance: dict,
    tech: dict,
    compliance: dict,
    validation: dict,
    fraud: dict,
    explanation: dict,
) -> bool:
    """
    Async entry point: Build and send evaluation result email with PDF attachment.
    Returns True on success, False on failure (never raises).
    """
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        logger.warning("SMTP_EMAIL or SMTP_APP_PASSWORD not set — skipping email notification.")
        return False

    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _send_sync(
                bidder_email=bidder_email,
                company_name=company_name,
                tender_title=tender_title,
                tender_number=tender_number,
                verdict=verdict,
                confidence=confidence,
                evaluation_id=evaluation_id,
                finance=finance,
                tech=tech,
                compliance=compliance,
                validation=validation,
                fraud=fraud,
                explanation=explanation,
            )
        )
        logger.info(f"Evaluation result email sent to {bidder_email} (verdict: {verdict})")
        return True
    except Exception as exc:
        logger.error(f"Failed to send evaluation email to {bidder_email}: {exc}")
        return False


def _send_sync(
    bidder_email: str,
    company_name: str,
    tender_title: str,
    tender_number: str,
    verdict: str,
    confidence: float,
    evaluation_id: str,
    finance: dict,
    tech: dict,
    compliance: dict,
    validation: dict,
    fraud: dict,
    explanation: dict,
):
    """Synchronous SMTP send — runs in executor thread."""
    # Collect red flags for email
    red_flags = []
    for agent in [finance, tech, compliance, validation, fraud]:
        red_flags.extend(agent.get("red_flags", []))
    for ind in fraud.get("fraud_indicators", []):
        red_flags.append(ind.get("description", ""))
    red_flags = list(set(red_flags))[:8]

    # Explanation summary
    summary = ""
    if isinstance(explanation, dict):
        summary = explanation.get("summary") or explanation.get("recommendation", "")
    if not summary:
        status_map = {"eligible": "passed all evaluation criteria", "not_eligible": "did not meet one or more mandatory criteria", "needs_review": "requires manual review by a procurement officer"}
        summary = f"Your application has {status_map.get(verdict, 'been processed')}."

    # Build HTML body
    html_body = _build_html_email(
        company_name=company_name,
        tender_title=tender_title,
        tender_number=tender_number,
        verdict=verdict,
        confidence=confidence,
        explanation=summary,
        evaluation_id=evaluation_id,
        red_flags=red_flags,
    )

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Karnataka e-Procurement] Bid Evaluation Result — {tender_number}"
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_EMAIL}>"
    msg["To"] = bidder_email
    msg["Reply-To"] = SMTP_EMAIL

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Attach PDF for rejected / needs_review bids
    if verdict in ("not_eligible", "needs_review"):
        try:
            pdf_bytes = _build_rejection_pdf(
                company_name=company_name,
                tender_title=tender_title,
                tender_number=tender_number,
                verdict=verdict,
                confidence=confidence,
                evaluation_id=evaluation_id,
                finance=finance,
                tech=tech,
                compliance=compliance,
                validation=validation,
                fraud=fraud,
                explanation=explanation,
            )
            pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_part.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"TenderSense_EvaluationReport_{evaluation_id[:8]}.pdf",
            )
            msg.attach(pdf_part)
            logger.info(f"Attached PDF rejection report ({len(pdf_bytes)} bytes) for {bidder_email}")
        except Exception as exc:
            logger.error(f"PDF generation failed: {exc} — sending email without PDF")

    # Send via SMTP
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_EMAIL, [bidder_email], msg.as_string())
