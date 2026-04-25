# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       17.04.2026
# Geaendert:      25.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch und das User Manual fuer build_reports als
#   PDF-Dateien (Deutsch und Englisch). Enthaelt alle Kapitel fuer
#   Nicht-Techniker: Einleitung, Dateien, GUI-Bedienung, Metriken-Erklaerungen
#   mit echten Beispieldiagrammen (aus den ART_A-Testdaten) und Tipps.
# =============================================================================

import sys
import tempfile
from datetime import date
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from version import __version__ as _VERSION

import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, Image as RLImage, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ---------------------------------------------------------------------------
# Test data paths (for chart generation)
# ---------------------------------------------------------------------------
_TESTDATA      = Path(__file__).parent.parent / "tests" / "testdata" / "ART_A"
_ISSUE_TIMES   = _TESTDATA / "ART_A_IssueTimes.xlsx"
_CFD_FILE      = _TESTDATA / "ART_A_CFD.xlsx"
_WORKFLOW_FILE = _TESTDATA / "workflow_ART_A.txt"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
C_BLUE   = colors.HexColor("#2c3e50")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")

OUTPUT_DE = Path(__file__).parent / "build_reports_Benutzerhandbuch.pdf"
OUTPUT_EN = Path(__file__).parent / "build_reports_UserManual.pdf"

CONTENT_WIDTH_CM = 15.5

LANG_DE = "de"
LANG_EN = "en"


# ---------------------------------------------------------------------------
# Chart image generation
# ---------------------------------------------------------------------------

def _generate_chart_images(out_dir: Path) -> dict[str, Path]:
    """
    Render all metric charts from the ART_A test dataset as PNG files.

    Uses the last 365 days of data relative to the latest closed date in the
    dataset. Flow Load and Flow Distribution use the full unfiltered dataset
    so that open issues are always included.

    Args:
        out_dir: Directory where PNG files are written.

    Returns:
        Dict mapping image key to PNG file path.
    """
    from build_reports.filters import FilterConfig, apply_filters
    from build_reports.loader import load_report_data
    from build_reports.metrics.cfd import CfdMetric
    from build_reports.metrics.flow_distribution import FlowDistributionMetric
    from build_reports.metrics.flow_load import FlowLoadMetric
    from build_reports.metrics.flow_time import FlowTimeMetric
    from build_reports.metrics.flow_velocity import FlowVelocityMetric
    from build_reports.terminology import SAFE

    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_report_data(_ISSUE_TIMES, _CFD_FILE, _WORKFLOW_FILE)

    closed = [i.closed_date for i in data.issues if i.closed_date]
    to_dt  = max(closed).date() if closed else date.today()
    from_dt = date(to_dt.year - 1, to_dt.month, to_dt.day)
    filtered = apply_filters(data, FilterConfig(from_date=from_dt, to_date=to_dt))

    def save(fig, name, w=1400, h=580):
        p = out_dir / f"{name}.png"
        pio.write_image(fig, str(p), format="png", width=w, height=h)
        return p

    imgs: dict[str, Path] = {}

    # Flow Time
    m = FlowTimeMetric()
    r = m.compute(filtered, SAFE)
    figs = m.render(r, SAFE)
    imgs["flow_time_box"]     = save(figs[0], "flow_time_box",     h=480)
    imgs["flow_time_scatter"] = save(figs[1], "flow_time_scatter", h=540)

    # Flow Velocity
    m = FlowVelocityMetric()
    r = m.compute(filtered, SAFE)
    figs = m.render(r, SAFE)
    imgs["velocity_daily"]  = save(figs[0], "velocity_daily",  h=460)
    imgs["velocity_weekly"] = save(figs[1], "velocity_weekly", h=480)
    imgs["velocity_pi"]     = save(figs[2], "velocity_pi",     h=480)

    # Flow Load (unfiltered – open issues must be present)
    m = FlowLoadMetric()
    r = m.compute(data, SAFE)
    figs = m.render(r, SAFE)
    imgs["flow_load"] = save(figs[0], "flow_load", h=540)

    # CFD
    m = CfdMetric()
    r = m.compute(filtered, SAFE)
    figs = m.render(r, SAFE)
    imgs["cfd"] = save(figs[0], "cfd", h=680)

    # Flow Distribution (unfiltered – all issue types should appear)
    m = FlowDistributionMetric()
    r = m.compute(data, SAFE)
    figs = m.render(r, SAFE)
    imgs["flow_dist"] = save(figs[0], "flow_dist", w=1600, h=560)

    return imgs


def _img(path: Path, width_cm: float = CONTENT_WIDTH_CM) -> RLImage:
    """
    Create a ReportLab Image flowable scaled to width_cm with correct aspect ratio.

    Args:
        path:      Path to the PNG file.
        width_cm:  Target display width in centimetres.

    Returns:
        RLImage flowable ready for insertion into a Platypus story.
    """
    ri = RLImage(str(path))
    aspect = ri.imageHeight / ri.imageWidth
    w = width_cm * cm
    return RLImage(str(path), width=w, height=w * aspect)


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def make_styles():
    """Build and return the paragraph style dictionary."""
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return dict(
        h1=s("H1", fontName="Helvetica-Bold", fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8, keepWithNext=1),
        h2=s("H2", fontName="Helvetica-Bold", fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5, keepWithNext=1),
        h3=s("H3", fontName="Helvetica-BoldOblique", fontSize=11, textColor=C_BLUE,
              spaceBefore=10, spaceAfter=4, keepWithNext=1),
        body=s("Body", fontName="Helvetica", fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("Bullet", fontName="Helvetica", fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3, bulletIndent=4),
        hint=s("Hint", fontName="Helvetica-Oblique", fontSize=9, textColor=C_HINT,
               leading=13, leftIndent=12, spaceAfter=4),
        caption=s("Caption", fontName="Helvetica-Oblique", fontSize=8,
                  textColor=C_HINT, leading=11, alignment=TA_CENTER, spaceAfter=8),
        code=s("Code", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

_HEADER_TEXT = {
    LANG_DE: "build_reports -- Benutzerhandbuch",
    LANG_EN: "build_reports -- User Manual",
}
_PAGE_LABEL = {
    LANG_DE: "Seite %d",
    LANG_EN: "Page %d",
}


class ManualDoc(BaseDocTemplate):
    """BaseDocTemplate with cover and normal page templates, language-aware headers."""

    def __init__(self, filename, lang: str = LANG_DE, **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        margin = 2.2 * cm
        w, h = A4
        self.addPageTemplates([
            PageTemplate(id="cover",
                         frames=[Frame(0, 0, w, h, id="cover", showBoundary=0)],
                         onPage=partial(build_cover, lang=lang)),
            PageTemplate(id="normal",
                         frames=[Frame(margin, margin,
                                       w - 2*margin, h - 2*margin - 1.2*cm,
                                       id="normal", showBoundary=0)],
                         onPage=self._header_footer),
        ])

    def _header_footer(self, canvas, doc):
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

    def afterFlowable(self, flowable):
        if hasattr(flowable, "toc_level"):
            self.notify("TOCEntry",
                        (flowable.toc_level, flowable.getPlainText(), self.page))


# ---------------------------------------------------------------------------
# Cover page (drawn via onPage callback)
# ---------------------------------------------------------------------------

_COVER_SUBTITLE = {
    LANG_DE: "Benutzerhandbuch",
    LANG_EN: "User Manual",
}
_COVER_TAGLINE = {
    LANG_DE: "Flow-Metriken fuer agile Teams - Einrichtung und Bedienung",
    LANG_EN: "Flow Metrics for Agile Teams - Setup and Usage",
}
_COVER_AUDIENCE = {
    LANG_DE: "Fuer nicht-technische Anwender",
    LANG_EN: "For non-technical users",
}


def build_cover(canvas, doc, lang: str = LANG_DE):
    """Draw the cover page with a blue/accent two-tone background and title block."""
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h*0.35, w, h*0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 32)
    canvas.drawCentredString(w/2, h*0.60, "build_reports")
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawCentredString(w/2, h*0.545, _COVER_SUBTITLE[lang])
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.49, _COVER_TAGLINE[lang])
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w*0.2, h*0.455, w*0.8, h*0.455)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w/2, h*0.12,
                             "situation-report - github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w/2, h*0.09,
                             f"{_COVER_AUDIENCE[lang]} — Version {_VERSION}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Helper flowables
# ---------------------------------------------------------------------------

class TocHeading(Paragraph):
    """Paragraph subclass that emits a TOC entry when rendered."""

    def __init__(self, text, style, level):
        super().__init__(text, style)
        self.toc_level = level


def H1(text, st): return TocHeading(text, st["h1"], 0)
def H2(text, st): return TocHeading(text, st["h2"], 1)
def H3(text, st): return TocHeading(text, st["h3"], 2)
def P(text, st):  return Paragraph(text, st["body"])
def BL(text, st): return Paragraph("- " + text, st["bullet"])
def HI(text, st): return Paragraph(text, st["hint"])
def CD(text, st): return Paragraph(text, st["code"])
def SP(n=6):      return Spacer(1, n)
def CAP(text, st): return Paragraph(text, st["caption"])


def box(text, st, bg="#eaf4fb"):
    """Return a styled info-box table with a coloured background."""
    tbl_obj = Table([[Paragraph(text, st["body"])]], colWidths=[16*cm])
    tbl_obj.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor(bg)),
        ("BOX",           (0,0), (-1,-1), 0.5, C_ACCENT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return tbl_obj


def tbl(headers, rows, col_widths=None):
    """Return a styled data table with a dark header row and alternating row colours."""
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_MID),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
    ]))
    return t


# ---------------------------------------------------------------------------
# Content – German
# ---------------------------------------------------------------------------

def content_de(st, images: dict[str, Path] | None = None):
    """
    Build the full German document story with optional embedded chart images.

    Args:
        st:     Style dict from make_styles().
        images: Dict of image key -> PNG path, or None to omit images.

    Returns:
        Tuple of (story list, TableOfContents instance).
    """
    story = []

    def add_img(key, caption_text, width_cm=CONTENT_WIDTH_CM):
        if images and key in images:
            story.append(SP(6))
            story.append(_img(images[key], width_cm))
            story.append(CAP(caption_text, st))

    # TOC
    story.append(PageBreak())
    story.append(H1("Inhalt", st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOCH1", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    story.append(toc)

    # =========================================================================
    # 1. Einleitung
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("1  Was ist build_reports?", st))
    story.append(P(
        "build_reports ist ein Werkzeug, das automatisch aussagekraeftige Diagramme "
        "ueber den Fortschritt und die Effizienz Ihres agilen Teams erstellt. "
        "Als Eingabe werden die Daten verwendet, die das Modul <b>transform_data</b> "
        "aus Ihrem Ticketsystem (z.&nbsp;B. Jira) exportiert hat. build_reports liest "
        "diese Dateien und berechnet daraus mehrere <b>Flow-Metriken</b> - grafische "
        "Auswertungen, die zeigen, wie schnell und wie viel Ihr Team liefert.", st))
    story.append(P(
        "Das Programm besitzt eine einfache grafische Oberflaeche (GUI): keine "
        "Programmierkenntnisse erforderlich. Per Knopfdruck werden die Diagramme im "
        "Browser angezeigt oder als PDF-Datei gespeichert.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Uebersicht der Metriken</b><br/>"
        "- <b>Flow Time / Cycle Time</b>: Wie lange dauert es, bis ein Issue fertig ist?<br/>"
        "- <b>Flow Velocity / Throughput</b>: Wie viele Issues schliesst das Team pro Woche ab?<br/>"
        "- <b>Flow Load / WIP</b>: Wie viele Issues sind gleichzeitig in Bearbeitung?<br/>"
        "- <b>Cumulative Flow Diagram</b>: Wie entwickelt sich der Bestand ueber die Zeit?<br/>"
        "- <b>Flow Distribution</b>: Wie verteilen sich die Issues auf Typen, Stages und Durchlaufzeiten?", st))

    # =========================================================================
    # 2. Voraussetzungen
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Voraussetzungen und Installation", st))

    story.append(H2("2.1  Was muss installiert sein?", st))
    story.append(P(
        "Damit build_reports funktioniert, muss auf dem Rechner <b>Python 3.11 oder "
        "neuer</b> installiert sein. Ausserdem muessen einige Python-Pakete vorhanden "
        "sein. Wer das Programm fuer Sie eingerichtet hat, sollte dies bereits erledigt "
        "haben.", st))

    story.append(H2("2.2  Programm starten", st))
    story.append(P("Es gibt zwei Moeglichkeiten, build_reports zu starten:", st))
    story.append(BL(
        "<b>Doppelklick</b> auf die Datei <b>build_reports_gui.pyw</b> im Projektordner "
        "-- oeffnet die grafische Oberflaeche ohne ein Konsolenfenster.", st))
    story.append(BL(
        "<b>Terminal / Eingabeaufforderung</b>: Ins Projektverzeichnis wechseln und "
        "<font name='Courier'>python -m build_reports</font> eingeben.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Wer die GUI regelmaessig nutzt, kann eine Verknuepfung zur Datei "
        "<b>build_reports_gui.pyw</b> auf dem Desktop erstellen.", st, "#e8f8f0"))

    # =========================================================================
    # 3. Eingabedateien
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("3  Eingabedateien", st))
    story.append(P(
        "build_reports benoetigt eine oder zwei Excel-Dateien, die vom Modul "
        "<b>transform_data</b> erstellt wurden. Diese Dateien duerfen nicht von Hand "
        "bearbeitet werden - der Aufbau muss exakt dem erwarteten Format entsprechen.",
        st))

    story.append(H2("3.1  IssueTimes.xlsx  (Pflichtdatei)", st))
    story.append(P(
        "Diese Datei enthaelt alle Issues (Tickets) mit ihren Zeitangaben und dem "
        "aktuellen Bearbeitungsstatus. Sie wird fuer alle Metriken ausser dem "
        "Cumulative Flow Diagram benoetigt.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Bedeutung"],
        [
            ["Project",       "Projektschluessel (z.B. ARTA)"],
            ["Key",           "Issue-Schluessel (z.B. ARTA-123)"],
            ["Issuetype",     "Typ des Issues (z.B. Feature, Bug, Story)"],
            ["Status",        "Aktueller Status (z.B. In Progress, Done)"],
            ["Created",       "Erstellungsdatum des Issues"],
            ["First Date",    "Datum, an dem das Issue erstmals aktiv bearbeitet wurde"],
            ["Closed Date",   "Datum des Abschlusses (leer = noch offen)"],
            ["Resolution",    "Abschlussart (z.B. Fixed, Duplicate)"],
            ["Stage-Spalten", "Je eine Spalte pro Workflow-Stage mit Minuten in dieser Stage"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.2  CFD.xlsx  (optional, fuer Cumulative Flow Diagram)", st))
    story.append(P(
        "Diese Datei enthaelt tagesgenaue Eintrittszaehlungen: wie viele Issues sind an "
        "diesem Tag in die jeweilige Stage <b>eingetreten</b> (keine Snapshots). "
        "build_reports akkumuliert diese Werte zu einem laufenden Gesamtwert. "
        "Sie wird nur benoetigt, wenn das Cumulative Flow Diagram berechnet werden soll.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Bedeutung"],
        [
            ["Day",           "Datum (YYYY-MM-DD)"],
            ["Stage-Spalten", "Je eine Spalte pro Stage mit der Anzahl neuer Eintritte an diesem Tag"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.3  PI-Konfigurationsdatei  (optional, fuer Flow Velocity)", st))
    story.append(P(
        "Mit einer optionalen JSON-Konfigurationsdatei koennen Sie eigene PI-Intervalle "
        "(Program Increments) fuer das Flow-Velocity-Balkendiagramm definieren. Ohne "
        "diese Datei werden automatisch Kalenderquartale verwendet.", st))
    story.append(SP(4))
    story.append(P("<b>Beispiel (Datumsmodus):</b>", st))
    story.append(CD(
        '{ "mode": "date",<br/>'
        '&nbsp;&nbsp;"intervals": [<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.1", "from": "2025-01-06", "to": "2025-04-04"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.2", "from": "2025-04-05", "to": "2025-07-04"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.3", "from": "2025-07-05", "to": "2025-10-03"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.4", "from": "2025-10-04", "to": "2026-01-02"}<br/>'
        '&nbsp;&nbsp;]<br/>'
        '}', st))
    story.append(P(
        "Die Datei muss die Endung <b>.json</b> haben. Kopieren Sie die mitgelieferte "
        "Beispieldatei <b>pi_config_example.json</b> und passen Sie die Datumsangaben "
        "und Namen an Ihre PI-Termine an. Das Format muss erhalten bleiben.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Hinweis:</b> Datumsangaben immer im Format <b>YYYY-MM-DD</b> (Jahr-Monat-Tag). "
        "Beispiel: 6. Januar 2025 = 2025-01-06.", st, "#fff8e1"))

    # =========================================================================
    # 4. GUI
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("4  Die grafische Oberflaeche (GUI)", st))
    story.append(P(
        "Nach dem Start oeffnet sich das Hauptfenster. Es besteht aus drei Bereichen: "
        "dem <b>Dateibereich</b> (oben), dem <b>Filterbereich</b> (Mitte) und dem "
        "<b>Aktionsbereich</b> (unten) mit dem Log-Fenster.", st))

    story.append(H2("4.1  Dateien laden", st))
    story.append(P("Laden Sie zuerst die benoetigten Dateien:", st))
    story.append(BL(
        "<b>IssueTimes</b> - Klicken Sie auf den Ordner-Button rechts neben dem Feld "
        "und waehlen Sie die <b>IssueTimes.xlsx</b>-Datei aus. Nach dem Laden erscheinen "
        "die verfuegbaren Projekte und Issuetypen automatisch im Log.", st))
    story.append(BL(
        "<b>CFD (optional)</b> - Waehlen Sie die <b>CFD.xlsx</b>-Datei, wenn Sie das "
        "Cumulative Flow Diagram benoetigen.", st))
    story.append(BL(
        "<b>Workflow (optional)</b> - Waehlen Sie die Workflow-Textdatei aus "
        "transform_data. Sie enthaelt <b>&lt;First&gt;</b>- und "
        "<b>&lt;Closed&gt;</b>-Marker, die festlegen, welche Stage-Grenzen die "
        "CFD-Trendlinien markieren.", st))
    story.append(BL(
        "<b>PI-Konfig (optional)</b> - Waehlen Sie Ihre JSON-Konfigurationsdatei fuer "
        "eigene PI-Intervalle. Lassen Sie das Feld leer, um Kalenderquartale zu "
        "verwenden.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Beim Hover ueber ein Eingabefeld erscheint ein Tooltip, der "
        "erklaert, wofuer das Feld verwendet wird.", st, "#e8f8f0"))

    story.append(H2("4.2  Filter setzen", st))
    story.append(P(
        "Mit Filtern schraenken Sie ein, welche Issues in die Auswertung einfliessen:",
        st))
    story.append(SP(4))
    story.append(tbl(
        ["Filter / Ausschluss", "Beschreibung"],
        [
            ["Von / Bis",
             "Nur Issues beruecksichtigen, die in diesem Zeitraum abgeschlossen wurden. "
             "Format: YYYY-MM-DD. Der Kalender-Button oeffnet einen Datums-Picker."],
            ["Letzte 365 Tage",
             "Setzt Von und Bis automatisch auf die letzten 365 Tage bis heute."],
            ["Projekte",
             "Nur bestimmte Projekte auswerten. Mehrere Projekte mit Komma trennen, "
             "z.B. ARTA, ARTB. Der Auswahl-Button zeigt alle verfuegbaren Projekte."],
            ["Issuetypen",
             "Nur bestimmte Issue-Typen auswerten, z.B. Feature, Bug. "
             "Leer lassen = alle Typen. Der Auswahl-Button zeigt eine Auswahlliste."],
            ["Ausschliessen: Status",
             "Issues mit bestimmten Jira-Status vollstaendig aus allen Metriken entfernen, "
             "z.B. 'Canceled'. Der Auswahl-Button zeigt alle vorhandenen Status."],
            ["Ausschliessen: Resolution",
             "Issues mit bestimmten Abschlussarten ausschliessen, z.B. 'Won't Do' oder "
             "'Duplicate'. Der Auswahl-Button zeigt alle vorhandenen Resolutions."],
            ["Zero-Day-Issues ausschliessen",
             "Checkbox: Issues, deren Durchlaufzeit (First bis Closed Date) kuerzer als "
             "der eingestellte Schwellwert ist, werden komplett entfernt. Standard: "
             "5 Minuten. Typisch fuer Issues, die manuell durch den Workflow geklickt "
             "wurden ohne echte Entwicklungsarbeit."],
        ],
        col_widths=[3.8*cm, 12.2*cm]))

    story.append(H2("4.3  Metriken und CT-Methode auswaehlen", st))
    story.append(P(
        "Ueber die Checkboxen waehlen Sie aus, welche Metriken berechnet werden sollen. "
        "Mit <b>Alle</b> und <b>Keine</b> koennen alle Checkboxen auf einmal gesetzt "
        "oder geleert werden.", st))
    story.append(SP(4))
    story.append(P(
        "Die <b>CT-Methode</b> bestimmt, wie die Durchlaufzeit (Cycle Time) berechnet "
        "wird - nur relevant fuer die Flow-Time-Metrik:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Methode", "Berechnung"],
        [
            ["Methode A (Standard)",
             "Differenz in Kalendertagen zwischen First Date und Closed Date. "
             "Einfach und nachvollziehbar."],
            ["Methode B",
             "Summe der Minuten in den einzelnen Workflow-Stages (letzte Stage "
             "ausgeschlossen), dividiert durch 1440. Misst nur aktive Bearbeitungszeit."],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(H2("4.4  Bericht erstellen", st))
    story.append(P("Sie haben zwei Moeglichkeiten:", st))
    story.append(BL(
        "<b>Im Browser anzeigen</b> - Alle Diagramme werden in Ihrem Standard-Browser "
        "geoeffnet. Die Diagramme sind dort vollstaendig interaktiv: Hineinzoomen, "
        "Datenpunkte per Hover-Tooltip inspizieren und einzelne Kategorien in der "
        "Legende ein- und ausblenden.", st))
    story.append(BL(
        "<b>Reports exportieren</b> - Alle Diagramme werden in eine mehrseitige PDF-Datei "
        "exportiert. Ein Speicherdialog fragt nach Dateiname und Speicherort. "
        "Zusaetzlich zur PDF werden automatisch zwei Excel-Dateien erstellt: eine "
        "Report-Excel mit allen Issues, Statusgruppen und Durchlaufzeiten sowie -- bei "
        "vorhandenen Zero-Day Issues -- eine separate Datei fuer diese Issues.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Hinweis:</b> Waehrend die Berechnungen laufen, ist die Oberflaeche kurz "
        "gesperrt. Der Fortschritt wird im Log-Fenster angezeigt. Bitte nicht schliessen "
        "oder klicken, bis das Log die Fertigmeldung zeigt.", st, "#fff8e1"))

    story.append(H2("4.5  Templates -- Konfiguration speichern und laden", st))
    story.append(P(
        "Im Menue <b>Templates</b> koennen Sie alle aktuellen Einstellungen "
        "(Dateipfade, Filter, Metrikauswahl, CT-Methode, Terminologie) als JSON-Datei "
        "speichern und spaeter wieder laden. So muessen Sie nicht jedes Mal alle Felder "
        "neu ausfuellen.", st))
    story.append(BL(
        "<b>Speichern...</b> - Waehlen Sie einen Speicherort und einen Namen fuer die "
        "Konfigurationsdatei (z.B. meinTeam_Quartalsbericht.json).", st))
    story.append(BL(
        "<b>Laden...</b> - Oeffnen Sie eine gespeicherte Konfigurationsdatei. Alle "
        "Felder werden automatisch befuellt. Falls eine gespeicherte Datei nicht mehr "
        "gefunden wird, erscheint ein Hinweis im Log.", st))

    story.append(H2("4.6  Sprache und Terminologie", st))
    story.append(P(
        "Im Menue <b>Optionen</b> koennen Sie Sprache und Terminologie umschalten:", st))
    story.append(BL(
        "<b>Sprache</b> - Wechselt zwischen Deutsch und Englisch. Alle Beschriftungen, "
        "Tooltips und Menupunkte werden sofort aktualisiert.", st))
    story.append(BL(
        "<b>Terminologie</b> - Wechselt zwischen <b>SAFe</b> und <b>Global</b>. "
        "Im SAFe-Modus heissen die Metriken z.B. 'Flow Time', im Global-Modus "
        "'Cycle Time'. Diese Umstellung betrifft nur die Bezeichnungen, nicht die "
        "Berechnungen.", st))

    # =========================================================================
    # 5. Metriken
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("5  Die Metriken im Ueberblick", st))
    story.append(P(
        "Dieser Abschnitt erklaert jede Metrik in einfachen Worten: was sie misst, "
        "was die Diagramme zeigen und wie man die Ergebnisse interpretiert. "
        "Die Beispieldiagramme stammen aus einem Beispiel-Datensatz.", st))

    # --- 5.1 Flow Time -------------------------------------------------------
    story.append(H2("5.1  Flow Time / Cycle Time", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Die Durchlaufzeit - also die Anzahl der Tage, die "
        "ein Issue von der ersten Bearbeitung bis zum Abschluss benoetigt. Je kuerzer, "
        "desto besser.", st))

    story.append(H3("Diagramm 1: Boxplot (Verteilung)", st))
    story.append(P(
        "Der Boxplot zeigt auf einen Blick, wie die Durchlaufzeiten verteilt sind. "
        "Im Kopf des Diagramms stehen die wichtigsten Kennzahlen:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Kennzahl", "Bedeutung"],
        [
            ["Min / Max",   "Kuerzeste und laengste gemessene Durchlaufzeit"],
            ["Q1 / Q3",     "25% bzw. 75% der Issues liegen unterhalb dieses Werts"],
            ["Median",      "Die mittlere Durchlaufzeit -- 50% der Issues liegen darunter"],
            ["Mittelwert",  "Durchschnittliche Durchlaufzeit (kann durch Ausreisser verzerrt sein)"],
            ["90d CT%",     "Anteil der Issues mit Durchlaufzeit <= 90 Tagen (Service Level Expectation)"],
            ["P85 / P95",   "85% bzw. 95% der Issues wurden innerhalb dieser Zeit fertig"],
            ["Std.abw.",    "Standardabweichung -- wie stark streuen die Werte?"],
            ["VK",          "Variationskoeffizient -- relative Streuung (kleiner = stabiler Prozess)"],
            ["Zero-Day",    "Anzahl Issues mit Durchlaufzeit 0 (von der Auswertung ausgeschlossen)"],
        ],
        col_widths=[3*cm, 13*cm]))
    story.append(SP(4))
    story.append(HI(
        "Roter Punkt im Boxplot = statistischer Ausreisser. Im Browser koennen Sie den "
        "Issue-Schluessel per Hover-Tooltip ablesen.", st))
    add_img("flow_time_box",
            "Abb. 1: Boxplot der Durchlaufzeiten -- Verteilung, Quartile und Statistik-Header.")

    story.append(H3("Diagramm 2: Scatterplot (Verlauf ueber Zeit)", st))
    story.append(P(
        "Jeder Punkt ist ein abgeschlossenes Issue. Die X-Achse zeigt das Abschlussdatum, "
        "die Y-Achse die Durchlaufzeit in Tagen. Farben und Referenzlinien helfen bei "
        "der Einordnung:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Bedeutung"],
        [
            ["Blauer Punkt",   "Normale Issues (unterhalb des 85. Perzentils)"],
            ["Oranger Punkt",  "Langsame Issues (zwischen 85. und 95. Perzentil)"],
            ["Roter Punkt",    "Sehr langsame Issues (oberhalb des 95. Perzentils)"],
            ["Blaue Kurve",    "LOESS-Trendlinie -- zeigt den Trend der Durchlaufzeit ueber die Zeit"],
            ["Rote Linie",     "Median-Referenzlinie"],
            ["Gruene Linie",   "85. Perzentil-Referenzlinie"],
            ["Cyan-Linie",     "95. Perzentil-Referenzlinie"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_time_scatter",
            "Abb. 2: Scatterplot -- Durchlaufzeit je Abschlussdatum mit LOESS-Trendlinie und Referenzlinien.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation:</b> Steigt die LOESS-Trendlinie nach rechts an, werden "
        "Issues mit der Zeit langsamer. Eine flache Linie signalisiert einen stabilen "
        "Prozess. Viele rote und orange Punkte deuten auf haeufige Engpaesse hin.", st))

    # --- 5.2 Flow Velocity ---------------------------------------------------
    story.append(H2("5.2  Flow Velocity / Throughput", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Der Durchsatz -- also wie viele Issues das Team pro "
        "Woche oder pro PI abschliesst. Eine konstant hohe Velocity zeigt ein "
        "lieferfaehiges Team.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Diagramm", "Zeigt"],
        [
            ["Tagesfrequenz (Histogramm)",
             "Wie oft kommt es vor, dass genau 1, 2, 3 ... Issues an einem Tag "
             "abgeschlossen werden. Zeigt typische Tagesleistungen."],
            ["Wochenverlauf (Linienchart)",
             "Anzahl der pro Woche abgeschlossenen Issues ueber den gesamten Zeitraum. "
             "Schwankungen und Trends werden sofort sichtbar."],
            ["PI-Verlauf (Balkendiagramm)",
             "Anzahl der abgeschlossenen Issues pro PI (Program Increment) oder Quartal. "
             "Die rote Linie zeigt den Durchschnitt. Balkenfarben: "
             "Grau = erster Balken; Orange = laufendes PI; Blau = abgeschlossene PIs; "
             "Hellgrau = zukuenftige PIs."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("velocity_daily",
            "Abb. 3: Tagesfrequenz -- Haeufigkeit der taeglichen Abschlussanzahl.")
    add_img("velocity_weekly",
            "Abb. 4: Wochenverlauf -- abgeschlossene Issues pro Kalenderwoche.")
    add_img("velocity_pi",
            "Abb. 5: PI-Verlauf -- abgeschlossene Issues pro PI oder Quartal mit Durchschnittslinie.")

    # --- 5.3 Flow Load -------------------------------------------------------
    story.append(H2("5.3  Flow Load / WIP  (Work in Progress)", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Wie viele Issues sich gerade gleichzeitig in "
        "Bearbeitung befinden und wie alt sie bereits sind. Zu viele parallele Issues "
        "verlangsamen die Lieferung (je mehr WIP, desto laenger die Durchlaufzeit).", st))
    story.append(SP(4))
    story.append(P(
        "Das Diagramm zeigt einen gruppierten Boxplot: jede Stage erhaelt eine Box, "
        "die das Alter (in Tagen) der aktuell dort befindlichen Issues zeigt. "
        "Einzelne Punkte stellen einzelne Issues dar -- im Browser sehen Sie den "
        "Issue-Schluessel beim Hover.", st))
    story.append(SP(4))
    story.append(P(
        "Gestrichelte Referenzlinien aus den abgeschlossenen Issues (Median, 85. "
        "Perzentil, 95. Perzentil) geben Orientierung: Issues, die bereits ueber dem "
        "95. Perzentil der abgeschlossenen Issues liegen, sind stark verzoegert.", st))
    add_img("flow_load",
            "Abb. 6: Flow Load -- Alter der offenen Issues je Stage mit Referenzlinien aus abgeschlossenen Issues.")

    # --- 5.4 CFD -------------------------------------------------------------
    story.append(H2("5.4  Cumulative Flow Diagram (CFD)", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Wie viele Issues insgesamt in jede Stage eingetreten "
        "sind -- kumuliert ueber die Zeit, aufgeteilt nach Workflow-Stage. Ein gut "
        "funktionierendes System zeigt parallele, gleichmaessig steigende Baender ohne "
        "Aufblehungen in einzelnen Stages.", st))
    story.append(SP(4))
    story.append(P(
        "Das Diagramm ist ein gestapeltes Flaechendiagramm: Jede farbige Schicht "
        "entspricht einer Stage. Die erste Stage liegt oben, die letzte (Done/Closed) "
        "unten. Das Diagramm beginnt immer bei 0 -- unabhaengig vom gewahlten Startdatum. "
        "Zwei schwarze Trendlinien zeigen:", st))
    story.append(BL(
        "<b>Obere Linie (Zufluss):</b> Verlaeuft an der visuellen Oberkante der "
        "&lt;First&gt;-Stage (Systemeintritt). Ohne Workflow-Datei: erste Stage.", st))
    story.append(BL(
        "<b>Untere Linie (Abfluss):</b> Verlaeuft an der visuellen Oberkante der "
        "&lt;Closed&gt;-Stage (Systemabschluss). Ohne Workflow-Datei: letzte Stage.", st))
    add_img("cfd",
            "Abb. 7: Cumulative Flow Diagram -- kumulierte Eintritte je Stage mit Zufluss- und Abfluss-Trendlinie.")
    story.append(SP(4))
    story.append(P(
        "Das <b>In/Out-Verhaeltnis</b> im Diagrammtitel (z.B. 'Ratio In/out 1.80 : 1') "
        "zeigt, ob mehr eingeht als abgeschlossen wird. Ein Wert von 1.0 bedeutet "
        "ausgewogenes System; Werte deutlich ueber 1.0 bedeuten wachsendes Backlog.",
        st))
    story.append(SP(4))
    story.append(P(
        "Die X-Achse zeigt Monatsgrenzen mit grosser Beschriftung (z.B. 'Jan 2025') "
        "und ISO-Kalenderwochen mit kleiner grauer Beschriftung (z.B. 'W03'), damit "
        "die Labels nicht ueberlappen.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Hinweis:</b> Das CFD benoetigt die optionale CFD.xlsx-Datei. Ohne diese "
        "Datei kann die CFD-Metrik nicht berechnet werden.", st, "#fff8e1"))

    # --- 5.5 Flow Distribution -----------------------------------------------
    story.append(H2("5.5  Flow Distribution", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Die Zusammensetzung aller Issues nach Typ, "
        "dominanter Stage und durchschnittlicher Durchlaufzeit. Zeigt auf einen Blick, "
        "welche Issue-Arten dominieren, wo Issues die meiste Zeit verbringen, und "
        "welche Typen am schnellsten oder langsamsten bearbeitet werden.", st))
    story.append(SP(4))
    story.append(P(
        "Das Diagramm besteht aus drei Teildiagrammen nebeneinander:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Diagramm", "Was wird gezeigt?"],
        [
            ["By Issue Type (Donut)",
             "Anzahl und Prozentanteil der Issues je Issuetyp. Alle Issues fliessen ein."],
            ["Stage Prominence (Donut)",
             "Fuer jedes Issue wird die Stage ermittelt, in der es die laengste Zeit "
             "verbracht hat. Das Diagramm zaehlt, wie haeufig jede Stage ueber alle "
             "Issues hinweg die dominante war. Bei abgeschlossenen Issues wird die "
             "terminale Done-Stage (aktueller Status) ausgeschlossen, damit "
             "Wartezeit nach dem Schliessen das Ergebnis nicht verfaelscht. "
             "Der Untertitel zeigt die Anzahl der beitragenden Issues (n=...). "
             "Issues ohne Stage-Daten werden nicht gezaehlt."],
            ["Avg Cycle Time by Type (Balken)",
             "Durchschnittliche Durchlaufzeit in Tagen je Issuetyp (Methode A: "
             "Closed Date - First Date). Nur Issues mit beiden Datumsfeldern und "
             "CT > 0 fliessen ein. Balkenbeschriftung im Format '15.0d'."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_dist",
            "Abb. 8: Flow Distribution -- Issue-Typ-Verteilung, Stage Prominence und Ø Cycle Time je Typ.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation Stage Prominence:</b> Dominiert eine Stage besonders haeufig, "
        "verweilen Issues dort ueberproportional lange -- ein moeglicher Engpass im Workflow. "
        "Abgeschlossene Issues werden einbezogen, ihre terminale Done-Stage jedoch "
        "ausgeblendet, damit tatsaechliche Bearbeitungsschwerpunkte sichtbar bleiben.", st))

    # =========================================================================
    # 6. PDF-Export
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("6  PDF-Export", st))
    story.append(P(
        "Der PDF-Export erzeugt eine mehrseitige PDF-Datei mit allen ausgewaehlten "
        "Diagrammen. Jedes Diagramm erscheint auf einer eigenen Seite.", st))
    story.append(SP(6))
    story.append(tbl(
        ["Schritt", "Aktion"],
        [
            ["1", "Dateien laden und Filter setzen (wie in Kapitel 4 beschrieben)."],
            ["2", "Gewuenschte Metriken per Checkbox auswaehlen."],
            ["3", "Auf 'Reports exportieren' klicken."],
            ["4", "Im Speicherdialog Dateiname und Speicherort waehlen und bestaetigen."],
            ["5", "Das Programm rechnet und exportiert; der Fortschritt erscheint im Log."],
            ["6", "Nach Abschluss stehen PDF und Report-Excel am gewaehlten Speicherort bereit."],
        ],
        col_widths=[1.5*cm, 14.5*cm]))
    story.append(SP(8))
    story.append(H2("6.1  Automatische Report-Excel", st))
    story.append(P(
        "Bei jedem PDF-Export wird automatisch eine Excel-Datei mit dem gleichen Namen "
        "erzeugt (z.B. report.xlsx neben report.pdf). Diese Datei enthaelt alle "
        "gefilterten Issues im IssueTimes-Format, ergaenzt um drei Spalten:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Inhalt"],
        [
            ["Status Group",
             "Statusgruppe des Issues: 'To Do' (noch nicht gestartet), "
             "'In Progress' (in Bearbeitung) oder 'Done' (abgeschlossen). "
             "Abgeleitet aus First Date und Closed Date."],
            ["Cycle Time (First->Closed)",
             "Durchlaufzeit in Kalendertagen von First Date bis Closed Date "
             "(Methode A). Leer, wenn eines der Daten fehlt."],
            ["Cycle Time B (days in Status)",
             "Summe der Minuten in allen Workflow-Stages ausser der letzten, "
             "dividiert durch 1440 (Methode B). Leer, wenn eines der Daten fehlt."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(SP(8))
    story.append(box(
        "<b>Zero-Day Issues:</b> Zwei Mechanismen greifen unabhaengig voneinander:<br/>"
        "1. <b>Ausschluss-Filter (vor der Berechnung):</b> Ist die Checkbox "
        "'Zero-Day-Issues ausschliessen' aktiv, werden Issues mit einer Durchlaufzeit "
        "unterhalb des eingestellten Schwellwerts (Standard: 5 Minuten) komplett aus "
        "allen Metriken entfernt.<br/>"
        "2. <b>Innerhalb der Flow-Time-Metrik:</b> Issues mit einer Durchlaufzeit von "
        "0 Tagen (gleicher Kalendertag) werden separat ausgewiesen und nicht in die "
        "Statistik eingerechnet.<br/>"
        "In beiden Faellen wird eine separate Excel-Datei erstellt "
        "(z.B. report_zero_day_issues.xlsx im gleichen Ordner).", st,
        "#fff8e1"))

    # =========================================================================
    # 7. FAQ
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("7  Haeufige Fragen und Tipps", st))

    faqs = [
        (
            "Die Diagramme erscheinen nicht im Browser.",
            "Pruefen Sie, ob ein Standard-Browser eingestellt ist. Versuchen Sie "
            "alternativ den PDF-Export. Stellen Sie sicher, dass die IssueTimes-Datei "
            "korrekt geladen wurde (Log kontrollieren)."
        ),
        (
            "Der PDF-Export dauert sehr lange oder schlaegt fehl.",
            "Das Rendern der Diagramme als PDF benoetigt das Kaleido-Paket. Falls dies "
            "noch nicht eingerichtet wurde, wenden Sie sich an Ihren technischen "
            "Ansprechpartner."
        ),
        (
            "Im Log erscheint 'Stage nur in IssueTimes' oder 'Stage nur in CFD'.",
            "Die Stage-Spalten in IssueTimes.xlsx und CFD.xlsx stimmen nicht ueberein. "
            "Dies ist ein Hinweis, der die Auswertung nicht abbricht, aber darauf "
            "hindeutet, dass die Dateien aus unterschiedlichen Workflow-Versionen stammen."
        ),
        (
            "Wie kann ich nur ein bestimmtes Projekt auswerten?",
            "Geben Sie im Feld 'Projekte' den gewuenschten Projektschluessel ein "
            "(z.B. ARTA). Mehrere Projekte mit Komma trennen. Alternativ: Auswahl-Button "
            "fuer eine Liste aller verfuegbaren Projekte."
        ),
        (
            "Das Cumulative Flow Diagram erscheint nicht.",
            "Die CFD-Metrik benoetigt eine CFD.xlsx-Datei. Laden Sie diese im Feld "
            "'CFD (optional)'."
        ),
        (
            "Was ist der Unterschied zwischen PI-Intervallen und Quartalen?",
            "Standardmaessig werden Kalenderquartale (Q1-Q4) als Zeitabschnitte "
            "verwendet. Mit einer PI-Konfigurationsdatei koennen Sie eigene Zeitintervalle "
            "definieren, die Ihren tatsaechlichen PIs entsprechen -- zum Beispiel wenn "
            "Ihr PI am 6. Januar beginnt statt am 1. Januar."
        ),
        (
            "Wie sichere ich meine Einstellungen?",
            "Nutzen Sie das Menue 'Templates' -> 'Speichern...', um alle aktuellen "
            "Einstellungen in einer JSON-Datei zu sichern. Beim naechsten Mal: "
            "'Templates' -> 'Laden...'. Ausschluss-Einstellungen koennen zusaetzlich "
            "dauerhaft unter 'Templates' -> 'Ausschluesse als Standard speichern' "
            "hinterlegt werden."
        ),
        (
            "Ein Issue erscheint in den Metriken, obwohl es nie wirklich bearbeitet wurde.",
            "Das kommt vor, wenn ein Issue manuell innerhalb von Sekunden durch alle "
            "Workflow-Stages geklickt wurde -- ohne echte Entwicklungsarbeit. Aktivieren "
            "Sie in der GUI unter 'Ausschluesse' die Checkbox 'Zero-Day-Issues "
            "ausschliessen' (Schwellwert z.B. 5 Minuten). Das Issue wird dann komplett "
            "aus allen Metriken entfernt und in einer separaten Excel-Datei dokumentiert."
        ),
        (
            "Kann ich die Ergebnisse auch ohne Computer vorfahren?",
            "Ja: Exportieren Sie zunaechst einen PDF-Bericht. Die PDF-Datei enthaelt "
            "alle Diagramme und kann auf jedem Geraet geoeffnet werden. Fuer interaktive "
            "Praesentationen empfiehlt sich die Browser-Anzeige."
        ),
    ]
    for q, a in faqs:
        story.append(H3("F: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    # =========================================================================
    # 8. Glossar
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("8  Glossar", st))
    story.append(tbl(
        ["Begriff", "Erklaerung"],
        [
            ["Closed Date",    "Das Datum, an dem ein Issue abgeschlossen wurde."],
            ["Cycle Time",     "Andere Bezeichnung fuer Flow Time (Global-Terminologie)."],
            ["First Date",     "Datum der ersten aktiven Bearbeitung eines Issues."],
            ["Flow Load",      "Anzahl der aktuell in Bearbeitung befindlichen Issues (SAFe-Term)."],
            ["Flow Time",      "Durchlaufzeit von der ersten Bearbeitung bis zum Abschluss."],
            ["Flow Velocity",  "Anzahl abgeschlossener Issues pro Zeitraum (SAFe-Term)."],
            ["Issue",          "Ein Ticket im Ticketsystem (z.B. eine Jira-Karte)."],
            ["Issuetyp",       "Kategorie eines Issues, z.B. Feature, Bug, Story, Task."],
            ["IssueTimes",     "Die von transform_data erzeugte Excel-Datei mit allen Issues."],
            ["JSON",           "Einfaches Textformat fuer Konfigurationsdateien."],
            ["LOESS",          "Statistisches Glaettungsverfahren fuer Trendlinien."],
            ["P85 / P95",      "85. bzw. 95. Perzentil der Durchlaufzeiten."],
            ["PI",             "Program Increment -- ein fester Planungs- und Lieferzeitraum."],
            ["Resolution",     "Abschlussart eines Issues, z.B. 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework -- ein Framework fuer agile Skalierung."],
            ["Stage",          "Ein Schritt im Workflow, z.B. Analyse, Implementierung, Done."],
            ["Template",       "Gespeicherte Konfigurationsdatei mit allen Einstellungen."],
            ["Throughput",     "Andere Bezeichnung fuer Flow Velocity (Global-Terminologie)."],
            ["WIP",            "Work in Progress -- Issues, die aktuell in Bearbeitung sind."],
            ["Zero-Day Issue", "Issue, dessen Durchlaufzeit (First bis Closed Date) so kurz "
                               "ist, dass es keine echte Bearbeitungszeit repraesentiert. "
                               "Entsteht meist durch manuelles Durchklicken im Workflow. "
                               "Kann per Schwellwert-Filter aus allen Metriken entfernt werden."],
        ],
        col_widths=[4*cm, 12*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content – English
# ---------------------------------------------------------------------------

def content_en(st, images: dict[str, Path] | None = None):
    """
    Build the full English document story with optional embedded chart images.

    Args:
        st:     Style dict from make_styles().
        images: Dict of image key -> PNG path, or None to omit images.

    Returns:
        Tuple of (story list, TableOfContents instance).
    """
    story = []

    def add_img(key, caption_text, width_cm=CONTENT_WIDTH_CM):
        if images and key in images:
            story.append(SP(6))
            story.append(_img(images[key], width_cm))
            story.append(CAP(caption_text, st))

    # TOC
    story.append(PageBreak())
    story.append(H1("Contents", st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOCH1en", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2en", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3en", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    story.append(toc)

    # =========================================================================
    # 1. Introduction
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("1  What is build_reports?", st))
    story.append(P(
        "build_reports is a tool that automatically creates meaningful charts about the "
        "progress and efficiency of your agile team. As input it uses the data that the "
        "<b>transform_data</b> module has exported from your issue tracker (e.g. Jira). "
        "build_reports reads these files and calculates several <b>flow metrics</b> — "
        "graphical analyses showing how fast and how much your team delivers.", st))
    story.append(P(
        "The program has a simple graphical user interface (GUI): no programming "
        "knowledge required. At the click of a button, charts are displayed in the "
        "browser or saved as a PDF file.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Metrics overview</b><br/>"
        "- <b>Flow Time / Cycle Time</b>: How long does it take for an issue to be completed?<br/>"
        "- <b>Flow Velocity / Throughput</b>: How many issues does the team close per week?<br/>"
        "- <b>Flow Load / WIP</b>: How many issues are in progress simultaneously?<br/>"
        "- <b>Cumulative Flow Diagram</b>: How does the inventory develop over time?<br/>"
        "- <b>Flow Distribution</b>: How are issues distributed across types, stages and cycle times?", st))

    # =========================================================================
    # 2. Prerequisites
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Prerequisites and Installation", st))

    story.append(H2("2.1  What needs to be installed?", st))
    story.append(P(
        "For build_reports to work, <b>Python 3.11 or newer</b> must be installed on "
        "the computer. Additionally, several Python packages must be present. Whoever "
        "set up the program for you should have already handled this.", st))

    story.append(H2("2.2  Starting the program", st))
    story.append(P("There are two ways to start build_reports:", st))
    story.append(BL(
        "<b>Double-click</b> on the file <b>build_reports_gui.pyw</b> in the project "
        "folder — opens the graphical interface without a console window.", st))
    story.append(BL(
        "<b>Terminal / command prompt</b>: Navigate to the project directory and "
        "type <font name='Courier'>python -m build_reports</font>.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tip:</b> If you use the GUI regularly, you can create a shortcut to "
        "<b>build_reports_gui.pyw</b> on your desktop.", st, "#e8f8f0"))

    # =========================================================================
    # 3. Input files
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("3  Input Files", st))
    story.append(P(
        "build_reports requires one or two Excel files produced by the "
        "<b>transform_data</b> module. These files must not be edited manually — "
        "the structure must exactly match the expected format.", st))

    story.append(H2("3.1  IssueTimes.xlsx  (required)", st))
    story.append(P(
        "This file contains all issues (tickets) with their time data and current "
        "processing status. It is required for all metrics except the Cumulative "
        "Flow Diagram.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Column", "Meaning"],
        [
            ["Project",       "Project key (e.g. ARTA)"],
            ["Key",           "Issue key (e.g. ARTA-123)"],
            ["Issuetype",     "Type of issue (e.g. Feature, Bug, Story)"],
            ["Status",        "Current status (e.g. In Progress, Done)"],
            ["Created",       "Creation date of the issue"],
            ["First Date",    "Date on which the issue was first actively worked on"],
            ["Closed Date",   "Completion date (empty = still open)"],
            ["Resolution",    "Resolution type (e.g. Fixed, Duplicate)"],
            ["Stage columns", "One column per workflow stage with minutes spent in that stage"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.2  CFD.xlsx  (optional, for Cumulative Flow Diagram)", st))
    story.append(P(
        "This file contains daily entry counts: how many issues <b>entered</b> a given "
        "stage on each day (not snapshots). build_reports accumulates these values into "
        "a running total. It is only needed if the Cumulative Flow Diagram is to be "
        "calculated.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Column", "Meaning"],
        [
            ["Day",           "Date (YYYY-MM-DD)"],
            ["Stage columns", "One column per stage with the number of new entries on that day"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.3  PI configuration file  (optional, for Flow Velocity)", st))
    story.append(P(
        "With an optional JSON configuration file you can define your own PI intervals "
        "(Program Increments) for the Flow Velocity bar chart. Without this file, "
        "calendar quarters are used automatically.", st))
    story.append(SP(4))
    story.append(P("<b>Example (date mode):</b>", st))
    story.append(CD(
        '{ "mode": "date",<br/>'
        '&nbsp;&nbsp;"intervals": [<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.1", "from": "2025-01-06", "to": "2025-04-04"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.2", "from": "2025-04-05", "to": "2025-07-04"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.3", "from": "2025-07-05", "to": "2025-10-03"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.4", "from": "2025-10-04", "to": "2026-01-02"}<br/>'
        '&nbsp;&nbsp;]<br/>'
        '}', st))
    story.append(P(
        "The file must have a <b>.json</b> extension. Copy the provided example file "
        "<b>pi_config_example.json</b> and adjust the dates and names to match your "
        "PI schedule. The format must be preserved.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Note:</b> Always use date format <b>YYYY-MM-DD</b> (year-month-day). "
        "Example: January 6, 2025 = 2025-01-06.", st, "#fff8e1"))

    # =========================================================================
    # 4. GUI
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("4  The Graphical User Interface (GUI)", st))
    story.append(P(
        "After starting, the main window opens. It consists of three areas: "
        "the <b>file area</b> (top), the <b>filter area</b> (middle) and the "
        "<b>action area</b> (bottom) with the log window.", st))

    story.append(H2("4.1  Loading files", st))
    story.append(P("First load the required files:", st))
    story.append(BL(
        "<b>IssueTimes</b> — Click the folder button to the right of the field and "
        "select the <b>IssueTimes.xlsx</b> file. After loading, available projects and "
        "issue types appear automatically in the log.", st))
    story.append(BL(
        "<b>CFD (optional)</b> — Select the <b>CFD.xlsx</b> file if you need the "
        "Cumulative Flow Diagram.", st))
    story.append(BL(
        "<b>Workflow (optional)</b> — Select the workflow text file from transform_data. "
        "It contains <b>&lt;First&gt;</b> and <b>&lt;Closed&gt;</b> markers that "
        "determine which stage boundaries the CFD trend lines mark.", st))
    story.append(BL(
        "<b>PI config (optional)</b> — Select your JSON configuration file for custom "
        "PI intervals. Leave the field empty to use calendar quarters.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tip:</b> Hovering over an input field shows a tooltip explaining what the "
        "field is used for.", st, "#e8f8f0"))

    story.append(H2("4.2  Setting filters", st))
    story.append(P(
        "Filters restrict which issues are included in the analysis:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Filter / Exclusion", "Description"],
        [
            ["From / To",
             "Only consider issues closed within this date range. "
             "Format: YYYY-MM-DD. The calendar button opens a date picker."],
            ["Last 365 days",
             "Automatically sets From and To to the last 365 days up to today."],
            ["Projects",
             "Only analyse specific projects. Separate multiple projects with a comma, "
             "e.g. ARTA, ARTB. The selection button shows all available projects."],
            ["Issue types",
             "Only analyse specific issue types, e.g. Feature, Bug. "
             "Leave empty = all types. The selection button shows a pick list."],
            ["Exclude: Status",
             "Completely remove issues with certain Jira statuses from all metrics, "
             "e.g. 'Canceled'. The selection button shows all existing statuses."],
            ["Exclude: Resolution",
             "Exclude issues with certain resolution types, e.g. 'Won't Do' or "
             "'Duplicate'. The selection button shows all existing resolutions."],
            ["Exclude zero-day issues",
             "Checkbox: issues whose cycle time (First to Closed Date) is shorter than "
             "the configured threshold are removed completely. Default: 5 minutes. "
             "Typical for issues that were manually clicked through the workflow without "
             "any real development work."],
        ],
        col_widths=[3.8*cm, 12.2*cm]))

    story.append(H2("4.3  Selecting metrics and CT method", st))
    story.append(P(
        "Use the checkboxes to select which metrics should be calculated. "
        "The <b>All</b> and <b>None</b> buttons set or clear all checkboxes at once.",
        st))
    story.append(SP(4))
    story.append(P(
        "The <b>CT method</b> determines how cycle time is calculated — relevant "
        "only for the Flow Time metric:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Method", "Calculation"],
        [
            ["Method A (default)",
             "Difference in calendar days between First Date and Closed Date. "
             "Simple and straightforward."],
            ["Method B",
             "Sum of minutes in the individual workflow stages (last stage excluded), "
             "divided by 1440. Measures only active processing time."],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(H2("4.4  Creating a report", st))
    story.append(P("You have two options:", st))
    story.append(BL(
        "<b>Show in browser</b> — All charts are opened in your default browser. "
        "The charts are fully interactive there: zoom in, inspect data points via "
        "hover tooltip, and toggle individual categories in the legend.", st))
    story.append(BL(
        "<b>Export reports</b> — All charts are exported to a multi-page PDF file. "
        "A save dialog asks for file name and location. In addition to the PDF, two "
        "Excel files are automatically created: a report Excel with all issues, status "
        "groups and cycle times, and — if zero-day issues exist — a separate file for "
        "those issues.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Note:</b> While calculations are running, the interface is briefly locked. "
        "Progress is shown in the log window. Please do not close or click until the "
        "log shows the completion message.", st, "#fff8e1"))

    story.append(H2("4.5  Templates — saving and loading configuration", st))
    story.append(P(
        "In the <b>Templates</b> menu you can save all current settings "
        "(file paths, filters, metric selection, CT method, terminology) as a JSON "
        "file and reload them later — no need to fill in all fields every time.", st))
    story.append(BL(
        "<b>Save...</b> — Choose a location and a name for the configuration file "
        "(e.g. myTeam_QuarterlyReport.json).", st))
    story.append(BL(
        "<b>Load...</b> — Open a saved configuration file. All fields are filled in "
        "automatically. If a saved file can no longer be found, a note appears in the "
        "log.", st))

    story.append(H2("4.6  Language and terminology", st))
    story.append(P(
        "In the <b>Options</b> menu you can switch language and terminology:", st))
    story.append(BL(
        "<b>Language</b> — Switch between German and English. All labels, tooltips "
        "and menu items are updated immediately.", st))
    story.append(BL(
        "<b>Terminology</b> — Switch between <b>SAFe</b> and <b>Global</b>. "
        "In SAFe mode the metrics are called e.g. 'Flow Time', in Global mode "
        "'Cycle Time'. This switch affects only the labels, not the calculations.", st))

    # =========================================================================
    # 5. Metrics
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("5  Metrics Overview", st))
    story.append(P(
        "This section explains each metric in plain language: what it measures, "
        "what the charts show and how to interpret the results. "
        "The example charts are based on a sample dataset.", st))

    # --- 5.1 Flow Time -------------------------------------------------------
    story.append(H2("5.1  Flow Time / Cycle Time", st))
    story.append(P(
        "<b>What is measured?</b> The cycle time — i.e. the number of days an issue "
        "takes from first work to completion. Shorter is better.", st))

    story.append(H3("Chart 1: Box plot (distribution)", st))
    story.append(P(
        "The box plot shows at a glance how cycle times are distributed. "
        "The chart header contains the key statistics:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Statistic", "Meaning"],
        [
            ["Min / Max",   "Shortest and longest measured cycle time"],
            ["Q1 / Q3",     "25% / 75% of issues fall below this value"],
            ["Median",      "The middle cycle time — 50% of issues fall below it"],
            ["Mean",        "Average cycle time (can be skewed by outliers)"],
            ["90d CT%",     "Share of issues with cycle time <= 90 days (Service Level Expectation)"],
            ["P85 / P95",   "85% / 95% of issues were completed within this time"],
            ["Std dev",     "Standard deviation — how much do the values vary?"],
            ["CV",          "Coefficient of variation — relative spread (smaller = more stable process)"],
            ["Zero-Day",    "Number of issues with cycle time 0 (excluded from the analysis)"],
        ],
        col_widths=[3*cm, 13*cm]))
    story.append(SP(4))
    story.append(HI(
        "Red dot in the box plot = statistical outlier. In the browser you can read "
        "the issue key via hover tooltip.", st))
    add_img("flow_time_box",
            "Fig. 1: Box plot of cycle times — distribution, quartiles and statistics header.")

    story.append(H3("Chart 2: Scatter plot (trend over time)", st))
    story.append(P(
        "Each dot is a completed issue. The x-axis shows the completion date, "
        "the y-axis the cycle time in days. Colours and reference lines aid "
        "interpretation:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Meaning"],
        [
            ["Blue dot",    "Normal issues (below the 85th percentile)"],
            ["Orange dot",  "Slow issues (between 85th and 95th percentile)"],
            ["Red dot",     "Very slow issues (above the 95th percentile)"],
            ["Blue curve",  "LOESS trend line — shows the cycle time trend over time"],
            ["Red line",    "Median reference line"],
            ["Green line",  "85th percentile reference line"],
            ["Cyan line",   "95th percentile reference line"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_time_scatter",
            "Fig. 2: Scatter plot — cycle time per completion date with LOESS trend line and reference lines.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation:</b> If the LOESS trend line rises to the right, issues are "
        "getting slower over time. A flat line signals a stable process. Many red and "
        "orange dots indicate frequent bottlenecks.", st))

    # --- 5.2 Flow Velocity ---------------------------------------------------
    story.append(H2("5.2  Flow Velocity / Throughput", st))
    story.append(P(
        "<b>What is measured?</b> Throughput — i.e. how many issues the team closes "
        "per week or per PI. Consistently high velocity indicates a delivery-capable "
        "team.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Chart", "Shows"],
        [
            ["Daily frequency (histogram)",
             "How often exactly 1, 2, 3 ... issues are closed on a single day. "
             "Shows typical daily output."],
            ["Weekly trend (line chart)",
             "Number of issues closed per week over the entire period. "
             "Fluctuations and trends become immediately visible."],
            ["PI trend (bar chart)",
             "Number of issues closed per PI (Program Increment) or quarter. "
             "The red line shows the average. Bar colours: "
             "Grey = first bar; Orange = current PI; Blue = completed PIs; "
             "Light grey = future PIs."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("velocity_daily",
            "Fig. 3: Daily frequency — frequency of daily closure counts.")
    add_img("velocity_weekly",
            "Fig. 4: Weekly trend — issues closed per calendar week.")
    add_img("velocity_pi",
            "Fig. 5: PI trend — issues closed per PI or quarter with average line.")

    # --- 5.3 Flow Load -------------------------------------------------------
    story.append(H2("5.3  Flow Load / WIP  (Work in Progress)", st))
    story.append(P(
        "<b>What is measured?</b> How many issues are simultaneously in progress and "
        "how old they already are. Too many parallel issues slow down delivery "
        "(the more WIP, the longer the cycle time).", st))
    story.append(SP(4))
    story.append(P(
        "The chart shows a grouped box plot: each stage gets a box showing the age "
        "(in days) of the issues currently there. Individual dots represent individual "
        "issues — in the browser you see the issue key on hover.", st))
    story.append(SP(4))
    story.append(P(
        "Dashed reference lines from closed issues (median, 85th percentile, "
        "95th percentile) provide orientation: issues already above the 95th percentile "
        "of closed issues are significantly delayed.", st))
    add_img("flow_load",
            "Fig. 6: Flow Load — age of open issues per stage with reference lines from closed issues.")

    # --- 5.4 CFD -------------------------------------------------------------
    story.append(H2("5.4  Cumulative Flow Diagram (CFD)", st))
    story.append(P(
        "<b>What is measured?</b> How many issues in total have entered each stage — "
        "cumulated over time, broken down by workflow stage. A well-functioning system "
        "shows parallel, evenly rising bands without swelling in individual stages.", st))
    story.append(SP(4))
    story.append(P(
        "The chart is a stacked area diagram: each coloured layer corresponds to a "
        "stage. The first stage is at the top, the last (Done/Closed) at the bottom. "
        "The chart always starts at 0 — regardless of the selected start date. "
        "Two black trend lines show:", st))
    story.append(BL(
        "<b>Upper line (inflow):</b> Runs along the visual top edge of the "
        "&lt;First&gt; stage (system entry). Without a workflow file: first stage.", st))
    story.append(BL(
        "<b>Lower line (outflow):</b> Runs along the visual top edge of the "
        "&lt;Closed&gt; stage (system completion). Without a workflow file: last stage.",
        st))
    add_img("cfd",
            "Fig. 7: Cumulative Flow Diagram — cumulative entries per stage with inflow and outflow trend lines.")
    story.append(SP(4))
    story.append(P(
        "The <b>In/Out ratio</b> in the chart title (e.g. 'Ratio In/out 1.80 : 1') "
        "shows whether more is coming in than being completed. A value of 1.0 means a "
        "balanced system; values significantly above 1.0 indicate a growing backlog.",
        st))
    story.append(SP(4))
    story.append(P(
        "The x-axis shows month boundaries with large labels (e.g. 'Jan 2025') and "
        "ISO calendar weeks with small grey labels (e.g. 'W03'), so that labels do "
        "not overlap.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Note:</b> The CFD requires the optional CFD.xlsx file. Without this file "
        "the CFD metric cannot be calculated.", st, "#fff8e1"))

    # --- 5.5 Flow Distribution -----------------------------------------------
    story.append(H2("5.5  Flow Distribution", st))
    story.append(P(
        "<b>What is measured?</b> The composition of all issues by type, dominant "
        "stage and average cycle time. Shows at a glance which issue types dominate, "
        "where issues spend most time, and which types are processed fastest or "
        "slowest.", st))
    story.append(SP(4))
    story.append(P(
        "The chart consists of three sub-charts side by side:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Chart", "What is shown?"],
        [
            ["By Issue Type (donut)",
             "Count and percentage share of issues per issue type. All issues are included."],
            ["Stage Prominence (donut)",
             "For each issue the stage in which it spent the longest time is identified. "
             "The chart counts how often each stage was dominant across all issues. "
             "For closed issues the terminal Done stage (current status) is excluded, "
             "so that waiting time after closure does not distort the result. "
             "The subtitle shows the number of contributing issues (n=...). "
             "Issues without stage data are not counted."],
            ["Avg Cycle Time by Type (bar)",
             "Average cycle time in days per issue type (Method A: "
             "Closed Date - First Date). Only issues with both date fields and "
             "CT > 0 are included. Bar labels in format '15.0d'."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_dist",
            "Fig. 8: Flow Distribution — issue type distribution, Stage Prominence and avg cycle time per type.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation Stage Prominence:</b> If a stage dominates particularly "
        "often, issues linger there disproportionately long — a potential bottleneck in "
        "the workflow. Closed issues are included, but their terminal Done stage is "
        "hidden, so actual processing bottlenecks remain visible.", st))

    # =========================================================================
    # 6. PDF Export
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("6  PDF Export", st))
    story.append(P(
        "The PDF export creates a multi-page PDF file with all selected charts. "
        "Each chart appears on its own page.", st))
    story.append(SP(6))
    story.append(tbl(
        ["Step", "Action"],
        [
            ["1", "Load files and set filters (as described in Chapter 4)."],
            ["2", "Select desired metrics via checkboxes."],
            ["3", "Click 'Export reports'."],
            ["4", "In the save dialog, choose a file name and location and confirm."],
            ["5", "The program calculates and exports; progress appears in the log."],
            ["6", "After completion, the PDF and report Excel are available at the chosen location."],
        ],
        col_widths=[1.5*cm, 14.5*cm]))
    story.append(SP(8))
    story.append(H2("6.1  Automatic report Excel", st))
    story.append(P(
        "With every PDF export an Excel file with the same name is automatically "
        "created (e.g. report.xlsx next to report.pdf). This file contains all "
        "filtered issues in IssueTimes format, supplemented by three columns:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Column", "Content"],
        [
            ["Status Group",
             "Status group of the issue: 'To Do' (not yet started), "
             "'In Progress' (being worked on) or 'Done' (completed). "
             "Derived from First Date and Closed Date."],
            ["Cycle Time (First->Closed)",
             "Cycle time in calendar days from First Date to Closed Date "
             "(Method A). Empty if either date is missing."],
            ["Cycle Time B (days in Status)",
             "Sum of minutes in all workflow stages except the last, "
             "divided by 1440 (Method B). Empty if either date is missing."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(SP(8))
    story.append(box(
        "<b>Zero-day issues:</b> Two mechanisms operate independently:<br/>"
        "1. <b>Exclusion filter (before calculation):</b> If the checkbox "
        "'Exclude zero-day issues' is active, issues with a cycle time below the "
        "configured threshold (default: 5 minutes) are completely removed from all "
        "metrics.<br/>"
        "2. <b>Within the Flow Time metric:</b> Issues with a cycle time of 0 days "
        "(same calendar day) are reported separately and not included in the "
        "statistics.<br/>"
        "In both cases a separate Excel file is created "
        "(e.g. report_zero_day_issues.xlsx in the same folder).", st,
        "#fff8e1"))

    # =========================================================================
    # 7. FAQ
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("7  Frequently Asked Questions", st))

    faqs = [
        (
            "The charts do not appear in the browser.",
            "Check whether a default browser is configured. Alternatively try the PDF "
            "export. Make sure the IssueTimes file was loaded correctly (check the log)."
        ),
        (
            "The PDF export takes very long or fails.",
            "Rendering charts as PDF requires the Kaleido package. If this has not yet "
            "been set up, contact your technical contact."
        ),
        (
            "The log shows 'Stage only in IssueTimes' or 'Stage only in CFD'.",
            "The stage columns in IssueTimes.xlsx and CFD.xlsx do not match. This is a "
            "warning that does not stop the analysis, but indicates that the files come "
            "from different workflow versions."
        ),
        (
            "How can I analyse only a specific project?",
            "Enter the desired project key in the 'Projects' field (e.g. ARTA). "
            "Separate multiple projects with a comma. Alternatively: use the selection "
            "button for a list of all available projects."
        ),
        (
            "The Cumulative Flow Diagram does not appear.",
            "The CFD metric requires a CFD.xlsx file. Load it in the 'CFD (optional)' "
            "field."
        ),
        (
            "What is the difference between PI intervals and quarters?",
            "By default, calendar quarters (Q1-Q4) are used as time intervals. With a "
            "PI configuration file you can define your own intervals that match your "
            "actual PIs — for example if your PI starts on January 6 instead of "
            "January 1."
        ),
        (
            "How do I save my settings?",
            "Use the menu 'Templates' -> 'Save...' to save all current settings in a "
            "JSON file. Next time: 'Templates' -> 'Load...'. Exclusion settings can "
            "additionally be stored permanently under 'Templates' -> 'Save exclusions "
            "as default'."
        ),
        (
            "An issue appears in the metrics even though it was never really worked on.",
            "This happens when an issue was manually clicked through all workflow stages "
            "within seconds — without any real development work. Enable the checkbox "
            "'Exclude zero-day issues' under 'Exclusions' in the GUI (threshold e.g. "
            "5 minutes). The issue is then completely removed from all metrics and "
            "documented in a separate Excel file."
        ),
        (
            "Can I present the results without a computer?",
            "Yes: first export a PDF report. The PDF file contains all charts and can "
            "be opened on any device. For interactive presentations, the browser view "
            "is recommended."
        ),
    ]
    for q, a in faqs:
        story.append(H3("Q: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    # =========================================================================
    # 8. Glossary
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("8  Glossary", st))
    story.append(tbl(
        ["Term", "Explanation"],
        [
            ["Closed Date",    "The date on which an issue was completed."],
            ["Cycle Time",     "Alternative term for Flow Time (Global terminology)."],
            ["First Date",     "Date of the first active work on an issue."],
            ["Flow Load",      "Number of issues currently in progress (SAFe term)."],
            ["Flow Time",      "Cycle time from first work to completion."],
            ["Flow Velocity",  "Number of issues completed per time period (SAFe term)."],
            ["Issue",          "A ticket in the issue tracker (e.g. a Jira card)."],
            ["Issue type",     "Category of an issue, e.g. Feature, Bug, Story, Task."],
            ["IssueTimes",     "The Excel file with all issues produced by transform_data."],
            ["JSON",           "Simple text format for configuration files."],
            ["LOESS",          "Statistical smoothing method for trend lines."],
            ["P85 / P95",      "85th / 95th percentile of cycle times."],
            ["PI",             "Program Increment — a fixed planning and delivery period."],
            ["Resolution",     "Resolution type of an issue, e.g. 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework — a framework for agile scaling."],
            ["Stage",          "A step in the workflow, e.g. Analysis, Implementation, Done."],
            ["Template",       "Saved configuration file with all settings."],
            ["Throughput",     "Alternative term for Flow Velocity (Global terminology)."],
            ["WIP",            "Work in Progress — issues that are currently being worked on."],
            ["Zero-day issue", "An issue whose cycle time (First to Closed Date) is so short "
                               "that it does not represent real processing time. Usually caused "
                               "by manually clicking through the workflow. Can be removed from "
                               "all metrics via a threshold filter."],
        ],
        col_widths=[4*cm, 12*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Build helper
# ---------------------------------------------------------------------------

def _build_doc(output: Path, lang: str, story_fn, title: str, subject: str,
               images: dict[str, Path] | None) -> None:
    """
    Build one PDF manual document.

    Args:
        output:   Output PDF path.
        lang:     Language constant (LANG_DE or LANG_EN).
        story_fn: Content function (content_de or content_en).
        title:    PDF document title metadata.
        subject:  PDF document subject metadata.
        images:   Pre-rendered chart images dict, or None.
    """
    st = make_styles()
    doc = ManualDoc(str(output), lang=lang, title=title,
                    author="Robert Seebauer", subject=subject)
    story: list = [Spacer(1, 1), NextPageTemplate("normal")]
    story_content, toc = story_fn(st, images)
    story.extend(story_content)
    doc.multiBuild(story)
    print(f"PDF created: {output}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Generate German and English build_reports user manual PDFs with chart images."""
    print("Generating chart images from ART_A test data...")
    tmp_dir = Path(tempfile.mkdtemp(prefix="br_manual_"))
    try:
        images = _generate_chart_images(tmp_dir)
        print(f"  {len(images)} chart(s) rendered.")

        _build_doc(
            OUTPUT_DE, LANG_DE, content_de,
            title="build_reports Benutzerhandbuch",
            subject="Flow-Metriken fuer agile Teams",
            images=images,
        )
        _build_doc(
            OUTPUT_EN, LANG_EN, content_en,
            title="build_reports User Manual",
            subject="Flow Metrics for Agile Teams",
            images=images,
        )
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
