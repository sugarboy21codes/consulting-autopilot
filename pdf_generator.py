"""
PDF generator for King Makers Consulting Autopilot.

Converts markdown diagnostic briefs into professionally styled PDF documents
using ReportLab. Design language inspired by top-tier consulting deliverables
(McKinsey, BCG, KPMG) with strong typographic hierarchy, branded color palette,
accent bars on section headers, and structured executive-grade layout.
"""

import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# King Makers Consulting Brand Palette
# Inspired by KPMG/McKinsey report styling: deep navy primary,
# warm gold accent, cool teal secondary, structured grays.
NAVY = HexColor("#0F1B2D")
NAVY_LIGHT = HexColor("#1A2B45")
GOLD = HexColor("#C9963B")
TEAL = HexColor("#1B6B93")
CHARCOAL = HexColor("#2D3748")
SLATE = HexColor("#4A5568")
SILVER = HexColor("#A0AEC0")
RULE_GRAY = HexColor("#CBD5E0")
LIGHT_BG = HexColor("#F7FAFC")
WHITE = HexColor("#FFFFFF")


def _build_styles():
    """Create the consulting-grade PDF stylesheet."""
    styles = {}

    # Document Title (H1): Large, navy, bold.
    styles["title"] = ParagraphStyle(
        "BriefTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    # Subtitle / Metadata line: Date, client name. Muted silver.
    styles["subtitle"] = ParagraphStyle(
        "BriefSubtitle",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=SILVER,
        alignment=TA_LEFT,
        spaceAfter=14,
    )

    # Section Header (H2): Bold, navy. Used with gold accent bar.
    styles["h2"] = ParagraphStyle(
        "Heading2",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=20,
        textColor=NAVY,
        spaceBefore=20,
        spaceAfter=8,
    )

    # Subsection Header (H3): Bold, teal.
    styles["h3"] = ParagraphStyle(
        "Heading3",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=16,
        textColor=TEAL,
        spaceBefore=14,
        spaceAfter=6,
    )

    # Body Text: Charcoal, generous leading for readability.
    styles["body"] = ParagraphStyle(
        "BodyText",
        fontName="Helvetica",
        fontSize=10,
        leading=16,
        textColor=CHARCOAL,
        spaceAfter=10,
        alignment=TA_LEFT,
    )

    # Bullet Points: Indented, tighter spacing between bullets.
    styles["bullet"] = ParagraphStyle(
        "BulletText",
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=CHARCOAL,
        spaceAfter=5,
        leftIndent=24,
        bulletIndent=12,
    )

    # Brand Header Text: Small, uppercase, gold.
    styles["brand_label"] = ParagraphStyle(
        "BrandLabel",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=GOLD,
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    # Footer
    styles["footer"] = ParagraphStyle(
        "Footer",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=SILVER,
        alignment=TA_CENTER,
    )

    return styles


def _convert_inline_formatting(text):
    """Convert markdown bold/italic to ReportLab XML tags."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = text.replace("&", "&amp;").replace("&amp;amp;", "&amp;")
    text = re.sub(r"<(?!/?[bi]>)", "&lt;", text)
    text = re.sub(r"(?<![bi])>", "&gt;", text)
    return text


def _draw_header_bar(canvas, doc):
    """Draw the branded header bar on the first page only."""
    width, height = letter

    canvas.saveState()

    # Gold accent line at the very top
    canvas.setFillColor(GOLD)
    canvas.rect(0, height - 4, width, 4, fill=1, stroke=0)

    # Navy bar below the gold line
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 40, width, 36, fill=1, stroke=0)

    # "KING MAKERS" in gold within the navy bar
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(GOLD)
    canvas.drawString(0.85 * inch, height - 28, "KING MAKERS")

    # "Consulting Autopilot" in white
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(WHITE)
    canvas.drawString(2.15 * inch, height - 28, "|   Consulting Autopilot")

    # Date/type marker on the right side
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#8899AA"))
    canvas.drawRightString(
        width - 0.85 * inch,
        height - 28,
        f"Diagnostic Brief  |  {datetime.now().strftime('%B %Y')}",
    )

    canvas.restoreState()


def _draw_footer(canvas, doc):
    """Draw professional footer on every page."""
    width, height = letter

    canvas.saveState()

    # Thin gold accent line above footer
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.5)
    canvas.line(0.85 * inch, 0.55 * inch, width - 0.85 * inch, 0.55 * inch)

    # Footer text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SILVER)
    canvas.drawString(
        0.85 * inch,
        0.38 * inch,
        "King Makers  |  kingmakersinc.ca  |  Confidential",
    )
    canvas.drawRightString(
        width - 0.85 * inch,
        0.38 * inch,
        f"Page {canvas.getPageNumber()}",
    )

    canvas.restoreState()


def _on_first_page(canvas, doc):
    """First page: header bar + footer."""
    _draw_header_bar(canvas, doc)
    _draw_footer(canvas, doc)


def _on_later_pages(canvas, doc):
    """Subsequent pages: footer only."""
    _draw_footer(canvas, doc)


def _add_section_header(story, text, styles):
    """Add an H2 section header with a gold accent bar on the left."""
    heading_para = Paragraph(text, styles["h2"])

    accent_table = Table(
        [[heading_para]],
        colWidths=[6.05 * inch],
        rowHeights=[None],
    )
    accent_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBEFORE", (0, 0), (0, 0), 3, GOLD),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(Spacer(1, 14))
    story.append(accent_table)
    story.append(Spacer(1, 4))


def markdown_to_pdf(markdown_text: str) -> bytes:
    """
    Convert a markdown diagnostic brief to a consulting-grade styled PDF.

    Design language: deep navy headers, gold accent bars on sections,
    teal subsection headers, charcoal body text, branded header strip
    on first page, professional footer with page numbers.

    Args:
        markdown_text: The raw markdown content of the diagnostic brief.

    Returns:
        The PDF file content as bytes.
    """
    buffer = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.9 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        title="Diagnostic Brief - King Makers",
        author="King Makers Consulting Autopilot",
    )

    story = []

    # Spacer below the header bar on page 1
    story.append(Spacer(1, 20))

    # Gold rule to separate header from content
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=GOLD,
            spaceAfter=16,
        )
    )

    # Parse markdown line by line
    lines = markdown_text.strip().split("\n")
    i = 0
    is_first_h1 = True

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # Horizontal rule
        if line in ("---", "***", "___"):
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=RULE_GRAY,
                    spaceBefore=10,
                    spaceAfter=10,
                )
            )
            i += 1
            continue

        # H1: # Title
        if line.startswith("# ") and not line.startswith("## "):
            text = _convert_inline_formatting(line[2:].strip())
            story.append(Paragraph(text, styles["title"]))

            if is_first_h1:
                date_str = datetime.now().strftime("%B %d, %Y")
                story.append(
                    Paragraph(
                        f"Generated {date_str}  |  King Makers Consulting Autopilot",
                        styles["subtitle"],
                    )
                )
                is_first_h1 = False

            i += 1
            continue

        # H2: ## Heading (with gold accent bar)
        if line.startswith("## "):
            text = _convert_inline_formatting(line[3:].strip())
            _add_section_header(story, text, styles)
            i += 1
            continue

        # H3: ### Heading
        if line.startswith("### "):
            text = _convert_inline_formatting(line[4:].strip())
            story.append(Paragraph(text, styles["h3"]))
            i += 1
            continue

        # Bullet points: - item or * item
        if line.startswith("- ") or line.startswith("* "):
            text = _convert_inline_formatting(line[2:].strip())
            bullet_text = (
                '<font color="#C9963B">\u25A0</font>'
                f"&nbsp;&nbsp;{text}"
            )
            story.append(Paragraph(bullet_text, styles["bullet"]))
            i += 1
            continue

        # Numbered list: 1. item
        numbered = re.match(r"^(\d+)\.\s+(.+)", line)
        if numbered:
            num = numbered.group(1)
            text = _convert_inline_formatting(numbered.group(2))
            num_text = (
                f'<font color="#C9963B"><b>{num}.</b></font>'
                f"&nbsp;&nbsp;{text}"
            )
            story.append(Paragraph(num_text, styles["bullet"]))
            i += 1
            continue

        # Regular paragraph
        paragraph_lines = []
        while i < len(lines):
            current = lines[i].strip()
            if (
                not current
                or current.startswith("#")
                or current.startswith("- ")
                or current.startswith("* ")
                or current in ("---", "***", "___")
                or re.match(r"^\d+\.\s+", current)
            ):
                break
            paragraph_lines.append(current)
            i += 1

        if paragraph_lines:
            text = " ".join(paragraph_lines)
            text = _convert_inline_formatting(text)
            story.append(Paragraph(text, styles["body"]))
            continue

        i += 1

    # End-of-document marker
    story.append(Spacer(1, 20))
    story.append(
        HRFlowable(
            width="40%",
            thickness=1.5,
            color=GOLD,
            spaceBefore=12,
            spaceAfter=8,
        )
    )
    story.append(
        Paragraph(
            "End of Diagnostic Brief",
            ParagraphStyle(
                "EndMarker",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=SILVER,
                alignment=TA_CENTER,
                spaceAfter=4,
            ),
        )
    )

    # Build PDF
    doc.build(
        story,
        onFirstPage=_on_first_page,
        onLaterPages=_on_later_pages,
    )
    buffer.seek(0)
    return buffer.read()
