# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Tutorial „Das Lagebild befragen (D3)" als PDF — DE und EN —
#   aus den mkdocs-Seiten docs/tutorials/ask-the-picture(.de).md. Eine
#   Quelle je Sprache: die Markdown-Seite ist die Wahrheit, das PDF ihre
#   druckbare Fassung mit denselben Bildschirmfotos (docs/tutorial_assets/
#   ask/). Unterstützt: Überschriften, Absätze, Listen, Tabellen, Code-
#   Blöcke, Zitate, Bilder mit Bildunterschrift, fett/kursiv/Code inline.
# =============================================================================

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS))
sys.path.insert(0, str(DOCS.parent))

from _font_config import setup as _setup_fonts  # noqa: E402

try:
    from version import __version__ as _VERSION
except ImportError:  # pragma: no cover
    _VERSION = "?"

FN, FB, FI, _FBI = _setup_fonts()
CONTENT_WIDTH = 175 * mm
ACCENT = colors.HexColor("#2b5b84")
BLUE = colors.HexColor("#1a3a56")
MUTED = colors.HexColor("#555555")
LIGHT = colors.HexColor("#eef3f8")

S = {
    "title": ParagraphStyle("t", fontName=FB, fontSize=21, leading=25, textColor=ACCENT),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=15, leading=19, spaceBefore=14, spaceAfter=6,
                         textColor=ACCENT),
    "h3": ParagraphStyle("h3", fontName=FB, fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=3,
                         textColor=BLUE),
    "body": ParagraphStyle("b", fontName=FN, fontSize=9.9, leading=13.8, spaceAfter=5),
    "li": ParagraphStyle("li", fontName=FN, fontSize=9.9, leading=13.4, leftIndent=13, spaceAfter=3),
    "code": ParagraphStyle("c", fontName="Courier", fontSize=8.2, leading=11.0,
                           backColor=colors.HexColor("#f4f4f4"), borderPadding=6, leftIndent=2,
                           spaceBefore=3, spaceAfter=8),
    "quote": ParagraphStyle("q", fontName=FI, fontSize=9.6, leading=13.4, leftIndent=10,
                            textColor=MUTED, spaceAfter=6),
    "cap": ParagraphStyle("cap", fontName=FI, fontSize=8.6, leading=11.5, textColor=MUTED,
                          spaceBefore=3, spaceAfter=10),
    "cell": ParagraphStyle("cell", fontName=FN, fontSize=8.6, leading=11.4),
    "cellh": ParagraphStyle("cellh", fontName=FB, fontSize=8.6, leading=11.4),
}

PAGES = {
    "de": (DOCS / "tutorials" / "ask-the-picture.de.md", DOCS / "ask_Tutorial_DE.pdf",
           "Das Lagebild befragen (D3) — Tutorial", "Seite"),
    "en": (DOCS / "tutorials" / "ask-the-picture.md", DOCS / "ask_Tutorial_EN.pdf",
           "Asking the situational picture (D3) — tutorial", "Page"),
}

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
_RULE_RE = re.compile(r":?-{3,}:?")


def inline(text: str) -> str:
    """Markdown inline markup → reportlab mini-HTML."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _IMAGE_RE.sub("", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)           # links: keep the text
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<font face='Courier' size='8.4'>\1</font>", text)
    return text


def _table(rows: list[list[str]]) -> Table:
    n = len(rows[0])
    widths = [CONTENT_WIDTH / n] * n
    if n == 2:
        widths = [CONTENT_WIDTH * 0.32, CONTENT_WIDTH * 0.68]
    data = [[Paragraph(inline(c), S["cellh" if r == 0 else "cell"]) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("GRID", (0, 0), (-1, -1), 0.4, MUTED),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _image(path: Path, caption: str, width_mm: float = 165) -> KeepTogether:
    from PIL import Image as PILImage

    with PILImage.open(path) as img:
        ratio = img.height / img.width
    width = min(width_mm * mm, CONTENT_WIDTH)
    flow = Image(str(path), width=width, height=width * ratio)
    flow.hAlign = "LEFT"
    return KeepTogether([flow, Paragraph(inline(caption), S["cap"])])


class _Converter:
    """Line-by-line Markdown → platypus, for the subset the tutorial pages use."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.story: list = []
        self.para: list[str] = []
        self.table: list[list[str]] = []
        self.quote: list[str] = []
        self.code: list[str] | None = None

    # -- buffers ------------------------------------------------------------
    def flush(self) -> None:
        if self.para:
            self.story.append(Paragraph(inline(" ".join(self.para)), S["body"]))
            self.para = []
        if self.table:
            self.story.extend([_table(self.table), Spacer(1, 4)])
            self.table = []
        if self.quote:
            self.story.append(Paragraph(inline(" ".join(self.quote)), S["quote"]))
            self.quote = []

    # -- line kinds ---------------------------------------------------------
    def _code_line(self, line: str) -> bool:
        if self.code is not None:
            if line.startswith("```"):
                self.story.append(Preformatted("\n".join(self.code), S["code"]))
                self.code = None
            else:
                self.code.append(line.replace("\t", "    "))
            return True
        if line.startswith("```"):
            self.flush()
            self.code = []
            return True
        return False

    def _heading(self, line: str) -> bool:
        for prefix, style in (("# ", "title"), ("## ", "h2"), ("### ", "h3")):
            if line.startswith(prefix):
                self.flush()
                self.story.append(Paragraph(inline(line[len(prefix):]), S[style]))
                if style == "title":
                    self.story += [Spacer(1, 2 * mm), HRFlowable(width="100%", thickness=1, color=ACCENT),
                                   Spacer(1, 3 * mm)]
                return True
        return False

    def _image_line(self, line: str) -> bool:
        m = _IMAGE_RE.match(line.strip())
        if not m:
            return False
        self.flush()
        self.story.append(_image((self.base / m.group(2)).resolve(), m.group(1)))
        return True

    def _table_line(self, line: str) -> bool:
        if not line.startswith("|"):
            if self.table:
                self.flush()
            return False
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(_RULE_RE.fullmatch(c) for c in cells):
            return True
        if self.para or self.quote:
            self.flush()
        self.table.append(cells)
        return True

    def _quote_line(self, line: str) -> bool:
        if line.startswith("> "):
            if self.para:
                self.flush()
            self.quote.append(line[2:])
            return True
        if self.quote:
            self.flush()
        return False

    def _list_line(self, line: str) -> bool:
        m = _LIST_RE.match(line)
        if not m:
            return False
        self.flush()
        mark = m.group(2) if m.group(2)[0].isdigit() else "•"
        style = ParagraphStyle("li2", parent=S["li"], leftIndent=13 + 10 * (len(m.group(1)) // 2))
        self.story.append(Paragraph(f"{mark}&nbsp;&nbsp;{inline(m.group(3))}", style))
        return True

    def feed(self, raw: str) -> None:
        line = raw.rstrip()
        if self._code_line(line) or self._heading(line) or self._image_line(line):
            return
        if line.strip() == "---" or not line.strip():
            self.flush()
            return
        if self._table_line(line) or self._quote_line(line) or self._list_line(line):
            return
        self.para.append(line.strip())

    def run(self, lines: list[str]) -> list:
        for raw in lines:
            self.feed(raw)
        self.flush()
        return self.story


def convert(md_path: Path) -> list:
    return _Converter(md_path.parent).run(md_path.read_text(encoding="utf-8").splitlines())


def _footer(label: str, page_word: str):
    def draw(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(FN, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 12 * mm, f"SituationReport {_VERSION} · {label}")
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"{page_word} {doc.page}")
        canvas.restoreState()
    return draw


def main() -> None:
    for src, out, title, page_word in PAGES.values():
        doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=17 * mm,
                                topMargin=16 * mm, bottomMargin=18 * mm, title=title,
                                author="Robert Seebauer")
        footer = _footer(title, page_word)
        doc.build(convert(src), onFirstPage=footer, onLaterPages=footer)
        print(f"PDF erstellt: {out}")


if __name__ == "__main__":
    main()
