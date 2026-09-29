#!/usr/bin/env python3
"""Render the dated architecture brief with a deliberately small Markdown subset.

Requires ReportLab. No network, credentials, repository mutation or model calls.
Relative links remain source-document references; HTTPS links are active in PDF.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#183049")
TEAL = colors.HexColor("#16746F")
INK = colors.HexColor("#263542")
MUTED = colors.HexColor("#5A6B79")
PALE = colors.HexColor("#EEF5F5")
RULE = colors.HexColor("#CFDCE3")
PAPER = colors.HexColor("#F5F8FA")


def inline(text: str) -> str:
    """Escape source first and emit only our supported, trusted formatting."""
    parts = re.split(r"(\[[^\]]+\]\([^\s)]+\)|`[^`]+`|\*\*[^*]+\*\*)", text)
    rendered = []
    for part in parts:
        link = re.fullmatch(r"\[([^\]]+)\]\(([^\s)]+)\)", part)
        if link:
            label, target = link.groups()
            label = html.escape(label)
            if target.startswith("https://"):
                rendered.append(
                    f'<a href="{html.escape(target, quote=True)}" color="#16746F">{label}</a>'
                )
            else:
                rendered.append(label)
        elif part.startswith("`") and part.endswith("`"):
            rendered.append(
                f'<font name="BriefMono" size="8.1">{html.escape(part[1:-1])}</font>'
            )
        elif part.startswith("**") and part.endswith("**"):
            rendered.append(f"<b>{html.escape(part[2:-2])}</b>")
        else:
            rendered.append(html.escape(part))
    return "".join(rendered)


def register_fonts(font_dir: Path | None) -> None:
    if font_dir is None:
        pdfmetrics.registerFontFamily(
            "Helvetica",
            normal="Helvetica",
            bold="Helvetica-Bold",
            italic="Helvetica-Oblique",
            boldItalic="Helvetica-BoldOblique",
        )
        # Stable names keep the renderer usable without bundled runtime fonts.
        from reportlab.pdfbase.pdfmetrics import Font

        for name, base in [
            ("Brief", "Helvetica"),
            ("BriefBold", "Helvetica-Bold"),
            ("BriefItalic", "Helvetica-Oblique"),
            ("BriefBoldItalic", "Helvetica-BoldOblique"),
            ("BriefMono", "Courier"),
        ]:
            pdfmetrics.registerFont(Font(name, base, "WinAnsiEncoding"))
    else:
        for name, filename in [
            ("Brief", "DejaVuSans.ttf"),
            ("BriefBold", "DejaVuSans-Bold.ttf"),
            ("BriefItalic", "DejaVuSans-Oblique.ttf"),
            ("BriefBoldItalic", "DejaVuSans-BoldOblique.ttf"),
            ("BriefMono", "DejaVuSansMono.ttf"),
        ]:
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    pdfmetrics.registerFontFamily(
        "Brief",
        normal="Brief",
        bold="BriefBold",
        italic="BriefItalic",
        boldItalic="BriefBoldItalic",
    )


class SystemDiagram(Flowable):
    """Original vector figures for relationships that benefit from spatial layout."""

    def __init__(self, kind: str, width: float):
        super().__init__()
        self.kind, self.width, self.height = kind, width, 164

    def draw(self):
        c = self.canv
        gap = 18
        boxw = (self.width - gap * 2) / 3

        def box(col, y, title, detail, accent=False):
            x = col * (boxw + gap)
            c.setFillColor(PALE if accent else PAPER)
            c.setStrokeColor(TEAL if accent else RULE)
            c.roundRect(x, y, boxw, 47, 5, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.setFont("BriefBold", 8.1)
            c.drawCentredString(x + boxw / 2, y + 29, title)
            c.setFont("Brief", 7.1)
            c.setFillColor(MUTED)
            c.drawCentredString(x + boxw / 2, y + 14, detail)

        def arrow(x1, y1, x2, y2, dashed=False):
            c.saveState()
            c.setStrokeColor(TEAL)
            c.setFillColor(TEAL)
            c.setLineWidth(1)
            if dashed:
                c.setDash(3, 2)
            c.line(x1, y1, x2, y2)
            c.setDash()
            from math import atan2, cos, sin

            a = atan2(y2 - y1, x2 - x1)
            p = c.beginPath()
            p.moveTo(x2, y2)
            for offset in (2.65, -2.65):
                p.lineTo(x2 + 5 * cos(a + offset), y2 + 5 * sin(a + offset))
            p.close()
            c.drawPath(p, fill=1, stroke=0)
            c.restoreState()

        def between(col, y):
            arrow(col * (boxw + gap) + boxw + 2, y, (col + 1) * (boxw + gap) - 3, y)

        if self.kind == "architecture":
            box(0, 105, "EXTERNAL SOURCES", "Papers / company research / X")
            box(1, 105, "EVIDENCE + CONTEXT", "Broker / captures / compiler")
            box(2, 105, "MANAGED EXECUTION", "Research / critique / proposal")
            box(0, 22, "COORDINATOR", "Admission / budget / audit", True)
            box(1, 22, "FROZEN EVALUATION", "Exact candidate / separate tasks", True)
            box(2, 22, "PUBLIC REPOSITORY", "Draft PR / human merge / skills")
            between(0, 129)
            between(1, 129)
            between(0, 46)
            between(1, 46)
            arrow(boxw / 2, 71, boxw + gap + boxw / 2, 102, True)
            arrow(2 * (boxw + gap) + boxw / 2, 102, boxw + gap + boxw / 2, 71)
        elif self.kind == "lifecycle":
            box(0, 105, "CAPTURE + RESEARCH", "Question / evidence / proposal")
            box(1, 105, "FREEZE + EVALUATE", "Independent, controlled tasks", True)
            box(2, 105, "QUALIFIED DRAFT PR", "Evidence and review packet")
            box(0, 22, "FAILURE MEMORY", "Reject / record / reprioritize")
            box(1, 22, "RELEASED KNOWLEDGE", "Skills / registry / provenance")
            box(2, 22, "HUMAN REVIEW", "Accept, revise or reject", True)
            between(0, 129)
            between(1, 129)
            arrow(boxw + gap + boxw / 2, 102, boxw / 2, 71)
            arrow(2 * (boxw + gap) + boxw / 2, 102, 2 * (boxw + gap) + boxw / 2, 71)
            arrow(2 * (boxw + gap) - 3, 46, boxw + gap + boxw + 2, 46)
            arrow(boxw / 2, 71, boxw / 2, 102, True)
        else:
            box(0, 105, "OPERATOR INTERFACE", "Restricted access / UI / API")
            box(1, 105, "SINGLE COORDINATOR", "One dedicated Linux host", True)
            box(2, 105, "LOCAL PRIVATE STATE", "SQLite / artifacts / secrets")
            box(0, 22, "SOURCE PROVIDERS", "Approved outbound retrieval")
            box(1, 22, "MANAGED AGENTS", "Remote provider execution")
            box(2, 22, "GITHUB DELIVERY", "Scoped draft-PR adapter")
            between(0, 129)
            between(1, 129)
            center = boxw + gap + boxw / 2
            for col in range(3):
                arrow(center, 102, col * (boxw + gap) + boxw / 2, 71)


class BriefDoc(BaseDocTemplate):
    def __init__(self, output: str):
        super().__init__(
            output,
            pagesize=A4,
            rightMargin=45,
            leftMargin=45,
            topMargin=51,
            bottomMargin=45,
            title="Toward a Living Research Repository",
            author="Agent Skills for Context Engineering",
            subject="Architecture, research agenda and launch roadmap; September 11, 2026",
        )
        self.section_title = "Architecture brief"
        self.section_pages: list[tuple[str, int]] = []
        self.addPageTemplates(
            PageTemplate(
                id="brief",
                frames=[
                    Frame(
                        self.leftMargin,
                        self.bottomMargin,
                        self.width,
                        self.height,
                        leftPadding=0,
                        rightPadding=0,
                        topPadding=0,
                        bottomPadding=0,
                    )
                ],
                onPage=self.page_chrome,
            )
        )

    def page_chrome(self, canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(TEAL)
        canvas.rect(self.leftMargin, h - 30, 25, 3, fill=1, stroke=0)
        canvas.setFont("BriefBold", 7.4)
        canvas.setFillColor(NAVY)
        canvas.drawString(
            self.leftMargin + 33, h - 29, "AGENT SKILLS / RESEARCH ARCHITECTURE"
        )
        canvas.setFont("Brief", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(w - self.rightMargin, h - 29, "11 SEP 2026")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.45)
        canvas.line(self.leftMargin, 33, w - self.rightMargin, 33)
        canvas.setFont("Brief", 7)
        canvas.drawString(
            self.leftMargin,
            21,
            "Working brief | Implemented, measured and proposed states distinguished",
        )
        canvas.drawRightString(w - self.rightMargin, 21, f"{doc.page:02d}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "Section":
            title = flowable.getPlainText()
            self.section_pages.append((title, self.page))
            key = f"section-{len(self.section_pages)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=0, closed=False)


def styles():
    common = dict(fontName="Brief", textColor=INK, alignment=TA_LEFT)
    return {
        "body": ParagraphStyle(
            "Body",
            **common,
            fontSize=9.7,
            leading=14.2,
            spaceAfter=9,
            splitLongWords=True,
        ),
        "title": ParagraphStyle(
            "CoverTitle",
            fontName="BriefBold",
            fontSize=28,
            leading=33,
            textColor=NAVY,
            spaceBefore=13,
            spaceAfter=16,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="BriefBold",
            fontSize=18,
            leading=23,
            textColor=NAVY,
            spaceAfter=15,
            keepWithNext=True,
        ),
        "sub": ParagraphStyle(
            "Subsection",
            fontName="BriefBold",
            fontSize=11,
            leading=15,
            textColor=TEAL,
            spaceBefore=6,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "cell": ParagraphStyle(
            "Cell",
            **common,
            fontSize=8,
            leading=11.1,
            spaceAfter=0,
            splitLongWords=True,
        ),
        "head": ParagraphStyle(
            "TableHead",
            fontName="BriefBold",
            fontSize=8.2,
            leading=11.2,
            textColor=colors.white,
            spaceAfter=0,
        ),
        "quote": ParagraphStyle(
            "Quote",
            **common,
            fontSize=10,
            leading=14.5,
            spaceAfter=13,
            spaceBefore=5,
            borderColor=TEAL,
            borderWidth=1,
            borderPadding=10,
            backColor=PALE,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            **common,
            fontSize=9.5,
            leading=13.8,
            leftIndent=12,
            firstLineIndent=-9,
            spaceAfter=7,
        ),
        "covermeta": ParagraphStyle(
            "CoverMeta",
            fontName="Brief",
            fontSize=11,
            leading=16,
            textColor=MUTED,
            spaceAfter=9,
        ),
    }


def table_flow(rows, width, sty):
    count = len(rows[0])
    if count == 2:
        if rows[0][0] == "ID":
            ratios = [0.18, 0.82]
        elif rows[0][0] == "Path in the integrated source tree":
            ratios = [0.46, 0.54]
        else:
            ratios = [0.31, 0.69]
    elif rows[0][0] == "PR":
        ratios = [0.09, 0.61, 0.30]
    elif rows[0][0] == "Planning allocation":
        ratios = [0.33, 0.10, 0.57]
    elif rows[0][0] == "Stage and owner":
        ratios = [0.27, 0.27, 0.46]
    elif count == 3:
        ratios = [0.26, 0.33, 0.41]
    else:
        ratios = [1 / count] * count
    parsed = [
        [Paragraph(inline(cell), sty["head" if i == 0 else "cell"]) for cell in row]
        for i, row in enumerate(rows)
    ]
    t = Table(
        parsed,
        colWidths=[width * ratio for ratio in ratios],
        repeatRows=1,
        hAlign="LEFT",
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, TEAL),
                ("LINEBELOW", (0, 1), (-1, -1), 0.35, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [t, Spacer(1, 12)]


def compile_markdown(source: str, width: float):
    sty = styles()
    lines = source.splitlines()
    flowables = []
    i = 0
    cover_meta = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "<!-- pagebreak -->":
            flowables.append(PageBreak())
            i += 1
            continue
        if line.startswith("# "):
            flowables.append(Paragraph(inline(line[2:]), sty["title"]))
            cover_meta = 3
            i += 1
            continue
        if line.startswith("## "):
            flowables.append(Paragraph(inline(line[3:]), sty["section"]))
            i += 1
            continue
        if line.startswith("### "):
            flowables.append(Paragraph(inline(line[4:]), sty["sub"]))
            i += 1
            continue
        if line.startswith("```"):
            kind = line[3:]
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                i += 1
            if kind not in {"architecture", "lifecycle", "deployment"}:
                raise ValueError(f"Unsupported diagram block: {kind}")
            flowables.append(SystemDiagram(kind, width))
            flowables.append(Spacer(1, 8))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            if any(len(row) != len(rows[0]) for row in rows):
                raise ValueError("Inconsistent Markdown table")
            flowables.extend(table_flow(rows, width, sty))
            continue
        if line.startswith("> "):
            flowables.append(Paragraph(inline(line[2:]), sty["quote"]))
            i += 1
            continue
        if line.startswith("- "):
            flowables.append(Paragraph("- " + inline(line[2:]), sty["bullet"]))
            i += 1
            continue
        if re.match(r"\d+\. ", line):
            flowables.append(Paragraph(inline(line), sty["bullet"]))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].startswith(("#", "|", "```", "<!--", "- ", "> "))
        ):
            paragraph.append(lines[i].strip())
            i += 1
        style = sty["covermeta"] if cover_meta else sty["body"]
        if cover_meta:
            cover_meta -= 1
        flowables.append(Paragraph(inline(" ".join(paragraph)), style))
    return flowables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    repo = here.parent.parent
    parser.add_argument(
        "--source",
        type=Path,
        default=here / "living-research-repository-architecture-2026-09-11.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo
        / "output/pdf/living-research-repository-architecture-2026-09-11.pdf",
    )
    parser.add_argument("--font-dir", type=Path)
    args = parser.parse_args()
    register_fonts(args.font_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc = BriefDoc(str(args.output))
    doc.build(compile_markdown(args.source.read_text(encoding="utf-8"), doc.width))
    print(f"Rendered {args.output}")
    for heading, page in doc.section_pages:
        print(f"{page:02d}  {heading}")


if __name__ == "__main__":
    main()
