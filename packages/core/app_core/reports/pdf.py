"""Vector PDF report generator for website audits and executive summaries."""

import io
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app_core.brand import BRAND


def generate_audit_pdf(
    *,
    domain: str,
    overall_score: int,
    category_scores: dict[str, int],
    summary: dict[str, int],
    issues: list[dict[str, Any]],
    generated_at: datetime | None = None,
    language: str = "en",
) -> bytes:
    """Generate professional executive PDF report using ReportLab."""
    if generated_at is None:
        generated_at = datetime.now(UTC)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_color = colors.HexColor("#2563EB")  # QuardLink Blue
    dark_text = colors.HexColor("#0F172A")
    muted_text = colors.HexColor("#64748B")
    border_color = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=dark_text,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=muted_text,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=dark_text,
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=dark_text,
    )
    issue_title_style = ParagraphStyle(
        "IssueTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=dark_text,
    )
    rec_style = ParagraphStyle(
        "RecommendationText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=muted_text,
    )

    story = []

    # 1. Header with branding
    header_data = [
        [
            Paragraph(f"<b>{BRAND['product_name']}</b> Executive SEO & AEO Report", title_style),
            Paragraph(
                f"Generated: <b>{generated_at.strftime('%Y-%m-%d %H:%M UTC')}</b><br/>Domain: <b>{domain}</b>",
                subtitle_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[340, 190])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_color, spaceAfter=15))

    # 2. Executive Scorecards
    score_boxes = [
        [
            Paragraph(
                f"<font size=18><b>{overall_score}</b></font>/100<br/><font color='#64748B' size=8>OVERALL SCORE</font>",
                body_style,
            ),
            Paragraph(
                f"<font size=18><b>{category_scores.get('technical', 0)}%</b></font><br/><font color='#64748B' size=8>TECHNICAL SEO</font>",
                body_style,
            ),
            Paragraph(
                f"<font size=18><b>{category_scores.get('content', 0)}%</b></font><br/><font color='#64748B' size=8>CONTENT QUALITY</font>",
                body_style,
            ),
            Paragraph(
                f"<font size=18><b>{category_scores.get('ai_readiness', 0)}%</b></font><br/><font color='#64748B' size=8>AI READINESS</font>",
                body_style,
            ),
            Paragraph(
                f"<font size=18><b>{category_scores.get('performance', 0)}%</b></font><br/><font color='#64748B' size=8>PERFORMANCE</font>",
                body_style,
            ),
        ]
    ]
    cards_table = Table(score_boxes, colWidths=[106, 106, 106, 106, 106])
    cards_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 1, border_color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(cards_table)
    story.append(Spacer(1, 15))

    # 3. Summary stats
    summary_text = (
        f"Audit checked <b>{summary.get('total_checks', len(issues))}</b> parameters across technical, content, AI answer engine compatibility, and Core Web Vitals. "
        f"<b>{summary.get('passed_checks', 0)}</b> passed successfully. "
        f"Discovered <b>{summary.get('total_issues', 0)}</b> items requiring attention "
        f"({summary.get('critical', 0)} critical, {summary.get('high', 0)} high priority, {summary.get('medium', 0)} medium, {summary.get('low', 0)} low)."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 12))

    # 4. Actionable Findings Table
    story.append(Paragraph("Actionable Findings & Recommendations", section_title))

    failed_issues = [i for i in issues if not i.get("passed", False)]
    if not failed_issues:
        story.append(
            Paragraph(
                "🎉 Excellent work! No critical SEO or AEO issues were found on this site.",
                body_style,
            )
        )
    else:
        table_rows = [
            [
                Paragraph("<b>Severity</b>", body_style),
                Paragraph("<b>Category</b>", body_style),
                Paragraph("<b>Issue & Recommendation</b>", body_style),
                Paragraph("<b>Fixable</b>", body_style),
            ]
        ]

        sev_colors = {
            "critical": colors.HexColor("#EF4444"),
            "high": colors.HexColor("#F97316"),
            "medium": colors.HexColor("#F59E0B"),
            "low": colors.HexColor("#64748B"),
        }

        # Show top issues (up to 15)
        for issue in failed_issues[:15]:
            sev = issue.get("severity", "medium")
            cat = issue.get("category", "technical").replace("_", " ").title()

            # Bilingual title/rec
            t_dict = issue.get("title", {})
            title_txt = t_dict.get(language) or t_dict.get("en") or issue.get("id", "Issue")
            r_dict = issue.get("recommendation", {})
            rec_txt = r_dict.get(language) or r_dict.get("en") or ""

            sev_label = f"<font color='{sev_colors.get(sev, colors.black).hexval()}'><b>{sev.upper()}</b></font>"
            details_cell = [
                Paragraph(title_txt, issue_title_style),
                Spacer(1, 2),
                Paragraph(f"Recommendation: {rec_txt}", rec_style),
            ]

            is_fixable = "Yes (Auto)" if issue.get("fixable", True) else "Manual"

            table_rows.append(
                [
                    Paragraph(sev_label, body_style),
                    Paragraph(cat, body_style),
                    details_cell,
                    Paragraph(is_fixable, body_style),
                ]
            )

        issues_table = Table(table_rows, colWidths=[70, 85, 305, 70])
        issues_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, border_color),
                    ("BOX", (0, 0), (-1, -1), 1, border_color),
                ]
            )
        )
        story.append(issues_table)

    story.append(Spacer(1, 20))

    # 5. Footer notice
    footer_text = (
        f"<font color='#94A3B8' size=8>This executive report was compiled by {BRAND['product_name']} "
        f"(https://quardlink.com) for {domain}. Confidential. All rights reserved.</font>"
    )
    story.append(Paragraph(footer_text, body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
