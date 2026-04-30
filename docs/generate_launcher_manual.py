# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.04.2026
# Geändert:       30.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch und das User Manual für den SituationReport
#   Launcher als PDF-Dateien (Deutsch und Englisch). Beschreibt Start,
#   Oberfläche, Module und Sprachumschaltung.
# =============================================================================

import sys
from datetime import date
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from version import __version__ as _VERSION

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

OUTPUT_DE = Path(__file__).parent / "launcher_Benutzerhandbuch.pdf"
OUTPUT_EN = Path(__file__).parent / "launcher_UserManual.pdf"

CONTENT_WIDTH_CM = 15.5
LANG_DE = "de"
LANG_EN = "en"

C_BLUE   = colors.HexColor("#2c3e50")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _make_styles() -> dict:
    """Build and return the paragraph style dictionary."""
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return dict(
        h1=s("H1", fontName="Helvetica-Bold", fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8),
        h2=s("H2", fontName="Helvetica-Bold", fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5),
        body=s("Body", fontName="Helvetica", fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("Bullet", fontName="Helvetica", fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3),
        code=s("Code", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
        hint=s("Hint", fontName="Helvetica-Oblique", fontSize=9, textColor=C_HINT,
               leading=13, leftIndent=12, spaceAfter=4),
        center=s("Center", fontName="Helvetica", fontSize=10, leading=15,
                 alignment=TA_CENTER, spaceAfter=6),
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

_HEADER_TEXT = {
    LANG_DE: "SituationReport Launcher  --  Benutzerhandbuch",
    LANG_EN: "SituationReport Launcher  --  User Manual",
}
_PAGE_LABEL = {LANG_DE: "Seite %d", LANG_EN: "Page %d"}


class _LauncherDoc(BaseDocTemplate):
    """BaseDocTemplate with cover and normal page templates."""

    def __init__(self, filename: str, lang: str = LANG_DE, **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        margin = 2.2 * cm
        w, h = A4
        self.addPageTemplates([
            PageTemplate(id="cover",
                         frames=[Frame(0, 0, w, h, id="cover", showBoundary=0)],
                         onPage=partial(_build_cover, lang=lang)),
            PageTemplate(id="normal",
                         frames=[Frame(margin, margin,
                                       w - 2*margin, h - 2*margin - 1.2*cm,
                                       id="normal", showBoundary=0)],
                         onPage=self._header_footer),
        ])

    def _header_footer(self, canvas, doc):
        """Draw header bar and page number."""
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(C_BLUE)
        canvas.rect(0, h - 1.1*cm, w, 1.1*cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(2.2*cm, h - 0.7*cm, _HEADER_TEXT[self._lang])
        canvas.drawRightString(w - 2.2*cm, h - 0.7*cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(w/2, 1.0*cm, _PAGE_LABEL[self._lang] % doc.page)
        canvas.setStrokeColor(C_MID)
        canvas.line(2.2*cm, 1.4*cm, w - 2.2*cm, 1.4*cm)
        canvas.restoreState()


def _build_cover(canvas, doc, lang: str = LANG_DE):
    """Draw the cover page."""
    w, h = A4
    subtitle = {"de": "Benutzerhandbuch", "en": "User Manual"}[lang]
    tagline = {
        "de": "Zentraler Einstiegspunkt für alle SituationReport-Module",
        "en": "Central entry point for all SituationReport modules",
    }[lang]
    audience = {
        "de": "Für alle Anwender — Version",
        "en": "For all users — Version",
    }[lang]

    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h*0.35, w, h*0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawCentredString(w/2, h*0.62, "SituationReport")
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(w/2, h*0.57, "Launcher")
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString(w/2, h*0.515, subtitle)
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.47, tagline)
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w*0.2, h*0.44, w*0.8, h*0.44)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w/2, h*0.12,
                             "situation-report — github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w/2, h*0.09, f"{audience} {_VERSION}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Table helper
# ---------------------------------------------------------------------------

_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), C_BLUE),
    ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
    ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",   (0, 0), (-1, 0), 10),
    ("ALIGN",      (0, 0), (-1, 0), "LEFT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
    ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE",   (0, 1), (-1, -1), 9),
    ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ("GRID",       (0, 0), (-1, -1), 0.4, C_MID),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING",   (0, 0), (-1, -1), 8),
])


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------

def _build_story_de(st: dict) -> list:
    """
    Build the German manual story (list of ReportLab flowables).

    Args:
        st: Style dictionary from _make_styles().

    Returns:
        List of Platypus flowables.
    """
    w = CONTENT_WIDTH_CM * cm
    story = [NextPageTemplate("normal"), PageBreak()]

    # ---- 1. Was ist der Launcher? ----
    story += [
        Paragraph("1. Was ist der Launcher?", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph(
            "Der SituationReport Launcher ist der zentrale Einstiegspunkt für alle "
            "Module der SituationReport-Toolsuite. Er zeigt alle verfügbaren und "
            "geplanten Module in einer übersichtlichen Kachel-Ansicht. Verfügbare "
            "Module lassen sich per Klick direkt starten — sie öffnen sich in einem "
            "eigenen Fenster, der Launcher bleibt geöffnet.", st["body"]),
        Spacer(1, 0.3*cm),

        # ---- 2. Starten ----
        Paragraph("2. Starten", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph("Aus dem portablen Paket (kein Python erforderlich):", st["h2"]),
        Table(
            [
                ["Betriebssystem", "Startdatei"],
                ["Windows",       "SituationReport.bat  (Doppelklick)"],
                ["macOS",         "SituationReport.command  (Rechtsklick → Öffnen)"],
                ["Linux",         "./SituationReport.sh"],
            ],
            colWidths=[4*cm, w - 4*cm],
            style=_TABLE_STYLE,
        ),
        Spacer(1, 0.3*cm),
        Paragraph("Aus dem Quellcode:", st["h2"]),
        Paragraph("python -m launcher", st["code"]),
        Spacer(1, 0.5*cm),

        # ---- 3. Die Oberfläche ----
        Paragraph("3. Die Oberfläche", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph(
            "Das Hauptfenster zeigt alle Module als Kacheln in einem 2-spaltigen "
            "Raster. Jede Kachel enthält ein Icon, den Modulnamen, eine kurze "
            "Beschreibung und — bei verfügbaren Modulen — einen <b>Starten</b>-Button. "
            "Geplante Module sind als <i>(bald verfügbar)</i> gekennzeichnet und "
            "können noch nicht gestartet werden.", st["body"]),
        Paragraph(
            "Oben rechts befinden sich der Sprachflag-Button (🌐) und der "
            "Manual-Button (?). Der Launcher bleibt nach dem Start eines Moduls "
            "geöffnet — es können mehrere Module gleichzeitig laufen.", st["body"]),
        Spacer(1, 0.5*cm),

        # ---- 4. Module ----
        Paragraph("4. Module", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Table(
            [
                ["Icon", "Modul", "Beschreibung", "Status"],
                ["📊", "Build Reports",      "Flow-Metriken und Reports erstellen", "verfügbar"],
                ["🔄", "Transform Data",     "Jira-Rohdaten in XLSX aufbereiten",   "verfügbar"],
                ["📥", "Get Data",           "Daten direkt aus Jira laden",         "geplant"],
                ["🎲", "Simulate",           "Prognosen und Simulationen",          "geplant"],
                ["🧪", "Testdata Generator", "Synthetische Testdaten erstellen",    "geplant"],
            ],
            colWidths=[1.2*cm, 3.8*cm, 7.5*cm, 3*cm],
            style=_TABLE_STYLE,
        ),
        Spacer(1, 0.5*cm),

        # ---- 5. Sprache ----
        Paragraph("5. Sprache", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph(
            "Die Sprache der Oberfläche wird über den Flag-Button oben rechts "
            "umgeschaltet. Jeder Klick wechselt zur nächsten Sprache in der Reihenfolge "
            "<b>DE → EN → RO → PT → FR → DE …</b>", st["body"]),
        Paragraph(
            "Die gewählte Sprache wird unter <font name='Courier'>~/.situation_report/prefs.json</font> "
            "gespeichert und gilt für alle Module gemeinsam.", st["body"]),
    ]
    return story


def _build_story_en(st: dict) -> list:
    """
    Build the English manual story (list of ReportLab flowables).

    Args:
        st: Style dictionary from _make_styles().

    Returns:
        List of Platypus flowables.
    """
    w = CONTENT_WIDTH_CM * cm
    story = [NextPageTemplate("normal"), PageBreak()]

    story += [
        Paragraph("1. What is the Launcher?", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph(
            "The SituationReport Launcher is the central entry point for all modules "
            "of the SituationReport toolsuite. It displays all available and planned "
            "modules in a clear tile view. Available modules can be launched with a "
            "single click — they open in their own window while the launcher remains "
            "open.", st["body"]),
        Spacer(1, 0.3*cm),

        Paragraph("2. Starting", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph("From the portable package (no Python required):", st["h2"]),
        Table(
            [
                ["Operating system", "Start file"],
                ["Windows",  "SituationReport.bat  (double-click)"],
                ["macOS",    "SituationReport.command  (right-click → Open)"],
                ["Linux",    "./SituationReport.sh"],
            ],
            colWidths=[4*cm, w - 4*cm],
            style=_TABLE_STYLE,
        ),
        Spacer(1, 0.3*cm),
        Paragraph("From source code:", st["h2"]),
        Paragraph("python -m launcher", st["code"]),
        Spacer(1, 0.5*cm),

        Paragraph("3. The Interface", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph(
            "The main window shows all modules as tiles in a 2-column grid. Each tile "
            "contains an icon, the module name, a short description, and — for available "
            "modules — a <b>Launch</b> button. Planned modules are labelled "
            "<i>(coming soon)</i> and cannot be started yet.", st["body"]),
        Paragraph(
            "The language flag button (🌐) and the manual button (?) are located in "
            "the top right. The launcher stays open after starting a module — "
            "multiple modules can run simultaneously.", st["body"]),
        Spacer(1, 0.5*cm),

        Paragraph("4. Modules", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Table(
            [
                ["Icon", "Module", "Description", "Status"],
                ["📊", "Build Reports",      "Create flow metrics and reports",    "available"],
                ["🔄", "Transform Data",     "Prepare raw Jira data as XLSX",      "available"],
                ["📥", "Get Data",           "Fetch data directly from Jira",      "planned"],
                ["🎲", "Simulate",           "Forecasts and simulations",          "planned"],
                ["🧪", "Testdata Generator", "Generate synthetic test data",       "planned"],
            ],
            colWidths=[1.2*cm, 3.8*cm, 7.5*cm, 3*cm],
            style=_TABLE_STYLE,
        ),
        Spacer(1, 0.5*cm),

        Paragraph("5. Language", st["h1"]),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        Paragraph(
            "The interface language is switched via the flag button in the top right. "
            "Each click advances to the next language in the sequence "
            "<b>DE → EN → RO → PT → FR → DE …</b>", st["body"]),
        Paragraph(
            "The selected language is saved in "
            "<font name='Courier'>~/.situation_report/prefs.json</font> "
            "and applies to all modules.", st["body"]),
    ]
    return story


# ---------------------------------------------------------------------------
# Workaround: NextPageTemplate as standalone flowable
# ---------------------------------------------------------------------------

from reportlab.platypus import ActionFlowable


class NextPageTemplate(ActionFlowable):
    """Switch the active page template for the next page break."""

    def __init__(self, pt):
        super().__init__(("nextPageTemplate", pt))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate DE and EN launcher manuals as PDF files."""
    st = _make_styles()

    for lang, output, story_fn in [
        (LANG_DE, OUTPUT_DE, _build_story_de),
        (LANG_EN, OUTPUT_EN, _build_story_en),
    ]:
        doc = _LauncherDoc(str(output), lang=lang)
        story = story_fn(st)
        doc.multiBuild(story)
        print(f"PDF created: {output}")


if __name__ == "__main__":
    main()
