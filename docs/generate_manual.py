# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       17.04.2026
# Geaendert:      28.04.2026
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
_TESTDATA         = Path(__file__).parent.parent / "tests" / "testdata" / "ART_A"
_ISSUE_TIMES      = _TESTDATA / "ART_A_IssueTimes.xlsx"
_CFD_FILE         = _TESTDATA / "ART_A_CFD.xlsx"
_WORKFLOW_FILE    = _TESTDATA / "workflow_ART_A.txt"
_TRANSITIONS_FILE = _TESTDATA / "ART_A_Transitions.xlsx"

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
OUTPUT_RO = Path(__file__).parent / "build_reports_ManualUtilizator.pdf"
OUTPUT_PT = Path(__file__).parent / "build_reports_ManualUtilizador.pdf"
OUTPUT_FR = Path(__file__).parent / "build_reports_ManuelUtilisateur.pdf"

CONTENT_WIDTH_CM = 15.5

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"


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
    from build_reports.metrics.process_flow import ProcessFlowMetric, ProcessFlowTimeMetric
    from build_reports.terminology import SAFE

    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_report_data(_ISSUE_TIMES, _CFD_FILE, _WORKFLOW_FILE, _TRANSITIONS_FILE)

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

    # Process Flow: Transitions (uses full dataset with transitions)
    m = ProcessFlowMetric()
    r = m.compute(data, SAFE)
    figs = m.render(r, SAFE)
    if figs:
        imgs["process_flow"] = save(figs[0], "process_flow", w=1400, h=700)

    # Process Flow: Time (uses full dataset with transitions)
    m = ProcessFlowTimeMetric()
    r = m.compute(data, SAFE)
    figs = m.render(r, SAFE)
    if figs:
        imgs["process_flow_time"] = save(figs[0], "process_flow_time", w=1400, h=700)

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
    LANG_RO: "build_reports -- Manual de Utilizator",
    LANG_PT: "build_reports -- Manual do Utilizador",
    LANG_FR: "build_reports -- Manuel d'utilisation",
}
_PAGE_LABEL = {
    LANG_DE: "Seite %d",
    LANG_EN: "Page %d",
    LANG_RO: "Pagina %d",
    LANG_PT: "Pagina %d",
    LANG_FR: "Page %d",
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
    LANG_RO: "Manual de Utilizator",
    LANG_PT: "Manual do Utilizador",
    LANG_FR: "Manuel d'utilisation",
}
_COVER_TAGLINE = {
    LANG_DE: "Flow-Metriken fuer agile Teams - Einrichtung und Bedienung",
    LANG_EN: "Flow Metrics for Agile Teams - Setup and Usage",
    LANG_RO: "Metrici de flux pentru echipe agile - Configurare si utilizare",
    LANG_PT: "Metricas de fluxo para equipas ageis - Configuracao e utilizacao",
    LANG_FR: "Metriques de flux pour equipes agiles - Configuration et utilisation",
}
_COVER_AUDIENCE = {
    LANG_DE: "Fuer nicht-technische Anwender",
    LANG_EN: "For non-technical users",
    LANG_RO: "Pentru utilizatori non-tehnici",
    LANG_PT: "Para utilizadores nao tecnicos",
    LANG_FR: "Pour les utilisateurs non techniques",
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
        ParagraphStyle("TOCH1de", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2de", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3de", fontName="Helvetica-Oblique", fontSize=8,
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
        "- <b>Flow Distribution</b>: Wie verteilen sich die Issues auf Typen, Stages und Durchlaufzeiten?<br/>"
        "- <b>Process Flow: Transitions</b>: Welche Statuspfade nehmen Issues? Wo treten Rueckschritte und Schleifen auf?<br/>"
        "- <b>Process Flow: Time</b>: Wie lange verweilen Issues in jeder Stage? Welche Uebergaenge kosten die meiste Zeit?", st))

    # =========================================================================
    # 2. Voraussetzungen
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Voraussetzungen und Installation", st))

    story.append(H2("2.1  Was muss installiert sein?", st))
    story.append(P(
        "build_reports wird als <b>portables Paket</b> geliefert. Eine separate "
        "Python-Installation ist nicht notwendig.", st))
    story.append(BL(
        "<b>Windows:</b> Python 3.11 ist bereits im Paket enthalten -- einfach "
        "entpacken und starten.", st))
    story.append(BL(
        "<b>macOS / Linux:</b> Beim ersten Start wird einmalig eine Python-Umgebung "
        "eingerichtet (ca. 1 Minute, Internet erforderlich). Danach laeuft die App offline.", st))

    story.append(H2("2.2  Programm starten", st))
    story.append(P(
        "Die passende Startdatei im entpackten Ordner doppelklicken:", st))
    story.append(BL(
        "<b>Windows:</b> <b>BuildReports.bat</b> doppelklicken -- startet die GUI "
        "ohne Konsolenfenster.", st))
    story.append(BL(
        "<b>macOS:</b> Rechtsklick auf <b>BuildReports.command</b> → <i>Oeffnen</i> "
        "(einmalig wegen Gatekeeper).", st))
    story.append(BL(
        "<b>Linux:</b> Im Terminal: "
        "<font name='Courier'>./BuildReports.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp (Windows):</b> Beim ersten Start erscheint moeglicherweise ein "
        "SmartScreen-Hinweis. Auf <b>Weitere Informationen</b> → "
        "<b>Trotzdem ausfuehren</b> klicken.", st, "#e8f8f0"))

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

    story.append(SP(8))
    story.append(H2("3.4  Transitions.xlsx  (optional, fuer Process Flow)", st))
    story.append(P(
        "Diese Datei enthaelt alle Statusuebergaenge je Issue in chronologischer "
        "Reihenfolge. Sie wird vom Modul <b>transform_data</b> erzeugt und ist "
        "ausschliesslich fuer die <b>Process-Flow-Metrik</b> erforderlich. "
        "Alle anderen Metriken koennen ohne diese Datei berechnet werden.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Bedeutung"],
        [
            ["Key",        "Issue-Schluessel (z.B. ARTA-123)"],
            ["Transition", "Ziel-Status nach dem Uebergang (z.B. 'In Analysis')"],
            ["Timestamp",  "Zeitstempel des Uebergangs (DD.MM.YYYY HH:MM:SS)"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(SP(4))
    story.append(box(
        "<b>Hinweis:</b> Transitions.xlsx und IssueTimes.xlsx muessen aus demselben "
        "transform_data-Lauf stammen, damit die Issue-Schluessel uebereinstimmen.", st, "#fff8e1"))

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
    story.append(BL(
        "<b>Transitions (optional)</b> - Waehlen Sie die <b>Transitions.xlsx</b>-Datei "
        "aus transform_data. Sie wird nur benoetigt, wenn die Process-Flow-Metrik "
        "berechnet werden soll.", st))
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
        "Die Sprache laesst sich auf zwei Wegen umschalten:", st))
    story.append(BL(
        "<b>Flaggen-Schaltflaeche</b> oben rechts im Fenster - zeigt die aktuelle "
        "Sprache als Landesflagge. Ein Klick wechselt sofort zwischen Deutsch und "
        "Englisch.", st))
    story.append(BL(
        "<b>Menue Optionen → Sprache</b> - alternativ ueber das Menue.", st))
    story.append(P(
        "Ueber <b>Optionen → Terminologie</b> laesst sich ausserdem zwischen "
        "<b>SAFe</b> und <b>Global</b> umschalten. Im SAFe-Modus heissen die Metriken "
        "z.B. 'Flow Time', im Global-Modus 'Cycle Time'. Diese Umstellung betrifft "
        "nur die Bezeichnungen, nicht die Berechnungen.", st))

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

    # --- 5.6 Process Flow: Transitions ---------------------------------------
    story.append(H2("5.6  Process Flow: Transitions", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Alle Statusuebergaenge der Issues werden als "
        "gerichteter Graph visualisiert: Knoten = Status, Pfeile = Uebergaenge. "
        "Die Pfeilstaerke ist proportional zur Haeufigkeit des Uebergangs. "
        "So sieht man auf einen Blick, welche Wege Issues durch den Workflow nehmen, "
        "wie haeufig Rueckschritte vorkommen und wo sich Issues 'im Kreis drehen'.", st))
    story.append(SP(4))
    story.append(P(
        "Fuer diese Metrik wird die optionale <b>Transitions.xlsx</b>-Datei benoetigt "
        "(aus transform_data). Ohne diese Datei erscheint eine Warnung im Log.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Bedeutung"],
        [
            ["Blauer Pfeil",   "Vorwaertsuebergang -- Issue bewegt sich im Workflow vorwaerts."],
            ["Roter Pfeil",    "Rueckwaertsuebergang (Rework) -- Issue geht in eine fruehere Stage zurueck."],
            ["Oranger Bogen",  "Self-Loop -- Issue verbleibt im selben Status (z.B. Stage erneut durchlaufen)."],
            ["Pfeilstaerke",   "Je dicker der Pfeil, desto haeufiger dieser Uebergang."],
            ["Zahl am Pfeil",  "Absolute Anzahl dieses Uebergangs ueber alle Issues."],
            ["Knoten",         "Dunkelblauer Kreis mit Status-Namen. Anordnung: Workflow-Stages zuerst (im Uhrzeigersinn), dann weitere Status alphabetisch."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow",
            "Abb. 9: Process Flow: Transitions -- gerichteter Graph aller Statusuebergaenge mit Kantenstaerke und Farbkodierung.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation:</b> Viele rote Pfeile bedeuten haeufige Rueckschritte -- "
        "ein Hinweis auf Qualitaetsprobleme oder unklare Anforderungen. "
        "Dicke blaue Pfeile zeigen den Haupt-Workflow-Pfad. "
        "Selbstschleifen (orange) entstehen z.B. wenn ein Issue mehrfach in denselben "
        "Status gesetzt wird.", st))

    # --- 5.7 Process Flow: Time ----------------------------------------------
    story.append(H2("5.7  Process Flow: Time", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Der gleiche gerichtete Graph wie Process Flow: Transitions, "
        "jedoch steht hier die <b>Zeit</b> im Vordergrund: Knotenbreite und Kantenbeschriftung "
        "basieren auf der medianen Verweildauer (Dwell Time) der Quell-Stage. "
        "So wird auf einen Blick sichtbar, in welchen Stages Issues am laengsten warten "
        "und welche Uebergaenge die meiste Zeit kosten.", st))
    story.append(SP(4))
    story.append(P(
        "Auch diese Metrik benoetigt die optionale <b>Transitions.xlsx</b>-Datei "
        "(aus transform_data).", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Bedeutung"],
        [
            ["Knotenbreite",      "Proportional zur medianen Verweildauer in dieser Stage."],
            ["Kantenbreite",      "Proportional zur medianen Verweildauer der Quell-Stage."],
            ["Zahl am Pfeil",     "Mediane Verweildauer der Quell-Stage in Tagen (d) fuer Issues, die genau diesen Uebergang genommen haben."],
            ["Blauer Pfeil",      "Vorwaertsuebergang."],
            ["Roter Pfeil",       "Rueckwaertsuebergang (Rework)."],
            ["Oranger Bogen",     "Self-Loop."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow_time",
            "Abb. 10: Process Flow: Time -- Knotenbreite und Kantenbeschriftung basieren auf der medianen Verweildauer je Stage.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation:</b> Breite Knoten und dicke Kanten zeigen Stages, in denen "
        "Issues besonders lange verweilen -- potenzielle Engpaesse. "
        "Verglichen mit Process Flow: Transitions laesst sich erkennen, ob haeufige "
        "Uebergaenge auch zeitlich ins Gewicht fallen oder nur kurze Statuswechsel sind.", st))

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
            "Der Process Flow zeigt 'No transition data available'.",
            "Die Process-Flow-Metrik benoetigt eine Transitions.xlsx-Datei aus "
            "transform_data. Laden Sie diese im Feld 'Transitions (optional)'. "
            "Stellen Sie sicher, dass die Datei aus demselben Exportlauf wie "
            "die IssueTimes.xlsx stammt."
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
            ["Process Flow: Transitions", "Gerichteter Graph aller Statusuebergaenge (haeufigkeitsbasiert). Zeigt Hauptpfade, Rueckschritte und Schleifen im Workflow."],
            ["Process Flow: Time",        "Gerichteter Graph aller Statusuebergaenge (zeitbasiert). Knotenbreite und Kantenbeschriftung zeigen die mediane Verweildauer je Stage."],
            ["Resolution",     "Abschlussart eines Issues, z.B. 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework -- ein Framework fuer agile Skalierung."],
            ["Stage",          "Ein Schritt im Workflow, z.B. Analyse, Implementierung, Done."],
            ["Template",       "Gespeicherte Konfigurationsdatei mit allen Einstellungen."],
            ["Throughput",     "Andere Bezeichnung fuer Flow Velocity (Global-Terminologie)."],
            ["Transitions",    "Aufzeichnung jedes Statuswechsels je Issue. Wird von transform_data als Transitions.xlsx exportiert."],
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
        "- <b>Flow Distribution</b>: How are issues distributed across types, stages and cycle times?<br/>"
        "- <b>Process Flow: Transitions</b>: Which status paths do issues take? Where do rework and loops occur?<br/>"
        "- <b>Process Flow: Time</b>: How long do issues dwell in each stage? Which transitions cost the most time?", st))

    # =========================================================================
    # 2. Prerequisites
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Prerequisites and Installation", st))

    story.append(H2("2.1  What needs to be installed?", st))
    story.append(P(
        "build_reports is delivered as a <b>portable package</b>. No separate Python "
        "installation is required.", st))
    story.append(BL(
        "<b>Windows:</b> Python 3.11 is already included in the package — just unzip "
        "and run.", st))
    story.append(BL(
        "<b>macOS / Linux:</b> On the first launch, a Python environment is set up "
        "automatically (approx. 1 minute, internet required). After that the app runs "
        "offline.", st))

    story.append(H2("2.2  Starting the program", st))
    story.append(P(
        "Double-click the appropriate launcher in the extracted folder:", st))
    story.append(BL(
        "<b>Windows:</b> Double-click <b>BuildReports.bat</b> — starts the GUI "
        "without a console window.", st))
    story.append(BL(
        "<b>macOS:</b> Right-click <b>BuildReports.command</b> → <i>Open</i> "
        "(once, to bypass Gatekeeper).", st))
    story.append(BL(
        "<b>Linux:</b> In a terminal: "
        "<font name='Courier'>./BuildReports.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tip (Windows):</b> On the first launch, SmartScreen may show a warning. "
        "Click <b>More info</b> → <b>Run anyway</b>.", st, "#e8f8f0"))

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

    story.append(SP(8))
    story.append(H2("3.4  Transitions.xlsx  (optional, for Process Flow)", st))
    story.append(P(
        "This file contains all status transitions per issue in chronological order. "
        "It is produced by the <b>transform_data</b> module and is required exclusively "
        "for the <b>Process Flow metric</b>. All other metrics can be calculated without "
        "this file.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Column", "Meaning"],
        [
            ["Key",        "Issue key (e.g. ARTA-123)"],
            ["Transition", "Target status after the transition (e.g. 'In Analysis')"],
            ["Timestamp",  "Timestamp of the transition (DD.MM.YYYY HH:MM:SS)"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(SP(4))
    story.append(box(
        "<b>Note:</b> Transitions.xlsx and IssueTimes.xlsx must come from the same "
        "transform_data export run so that issue keys match.", st, "#fff8e1"))

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
    story.append(BL(
        "<b>Transitions (optional)</b> — Select the <b>Transitions.xlsx</b> file from "
        "transform_data. Only required if the Process Flow metric is to be calculated.",
        st))
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
        "The language can be switched in two ways:", st))
    story.append(BL(
        "<b>Flag button</b> in the top-right corner of the window — shows the current "
        "language as a national flag. One click toggles instantly between German and "
        "English.", st))
    story.append(BL(
        "<b>Options → Language</b> menu — alternatively via the menu.", st))
    story.append(P(
        "Via <b>Options → Terminology</b> you can also switch between <b>SAFe</b> and "
        "<b>Global</b>. In SAFe mode the metrics are called e.g. 'Flow Time', in "
        "Global mode 'Cycle Time'. This switch affects only the labels, not the "
        "calculations.", st))

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

    # --- 5.6 Process Flow: Transitions ----------------------------------------
    story.append(H2("5.6  Process Flow: Transitions", st))
    story.append(P(
        "<b>What is measured?</b> All status transitions of issues are visualised as a "
        "directed graph: nodes = statuses, arrows = transitions. Arrow thickness is "
        "proportional to the frequency of the transition. This makes it immediately "
        "clear which paths issues take through the workflow, how often rework occurs, "
        "and where issues get stuck in loops.", st))
    story.append(SP(4))
    story.append(P(
        "This metric requires the optional <b>Transitions.xlsx</b> file (from "
        "transform_data). Without this file a warning appears in the log.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Meaning"],
        [
            ["Blue arrow",    "Forward transition — issue moves forward in the workflow."],
            ["Red arrow",     "Backward transition (rework) — issue returns to an earlier stage."],
            ["Orange arc",    "Self-loop — issue stays in the same status (e.g. stage traversed again)."],
            ["Arrow width",   "The thicker the arrow, the more frequent this transition."],
            ["Number on arrow", "Absolute count of this transition across all issues."],
            ["Node",          "Dark blue circle with status name. Order: workflow stages first "
                              "(clockwise), then additional statuses alphabetically."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow",
            "Fig. 9: Process Flow: Transitions — directed graph of all status transitions with edge width and colour coding.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation:</b> Many red arrows mean frequent rework — a sign of quality "
        "issues or unclear requirements. Thick blue arrows show the main workflow path. "
        "Self-loops (orange) occur when an issue is set to the same status multiple "
        "times.", st))

    # --- 5.7 Process Flow: Time -----------------------------------------------
    story.append(H2("5.7  Process Flow: Time", st))
    story.append(P(
        "<b>What is measured?</b> The same directed graph as Process Flow: Transitions, "
        "but with a focus on <b>time</b>: node width and edge labels are based on the "
        "median dwell time of the source stage. This makes it immediately visible in "
        "which stages issues wait the longest and which transitions cost the most time.", st))
    story.append(SP(4))
    story.append(P(
        "This metric also requires the optional <b>Transitions.xlsx</b> file "
        "(from transform_data).", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Meaning"],
        [
            ["Node width",       "Proportional to the median dwell time in this stage."],
            ["Edge width",       "Proportional to the median dwell time of the source stage."],
            ["Number on arrow",  "Median dwell time of the source stage in days (d) for issues that took exactly this transition."],
            ["Blue arrow",       "Forward transition."],
            ["Red arrow",        "Backward transition (rework)."],
            ["Orange arc",       "Self-loop."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow_time",
            "Fig. 10: Process Flow: Time — node width and edge labels based on the median dwell time per stage.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation:</b> Wide nodes and thick edges indicate stages where issues "
        "linger particularly long — potential bottlenecks. Compared with Process Flow: "
        "Transitions, you can see whether frequent transitions also carry significant "
        "time weight or are just brief status changes.", st))

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
            "Process Flow shows 'No transition data available'.",
            "The Process Flow metric requires a Transitions.xlsx file from transform_data. "
            "Load it in the 'Transitions (optional)' field. Make sure the file comes from "
            "the same export run as the IssueTimes.xlsx."
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
            ["Process Flow: Transitions", "Directed graph of all status transitions (frequency-based). Shows main paths, rework, and loops in the workflow."],
            ["Process Flow: Time",        "Directed graph of all status transitions (time-based). Node width and edge labels show the median dwell time per stage."],
            ["Resolution",     "Resolution type of an issue, e.g. 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework — a framework for agile scaling."],
            ["Stage",          "A step in the workflow, e.g. Analysis, Implementation, Done."],
            ["Template",       "Saved configuration file with all settings."],
            ["Throughput",     "Alternative term for Flow Velocity (Global terminology)."],
            ["Transitions",    "Record of every status change per issue. Exported by transform_data as Transitions.xlsx."],
            ["WIP",            "Work in Progress — issues that are currently being worked on."],
            ["Zero-day issue", "An issue whose cycle time (First to Closed Date) is so short "
                               "that it does not represent real processing time. Usually caused "
                               "by manually clicking through the workflow. Can be removed from "
                               "all metrics via a threshold filter."],
        ],
        col_widths=[4*cm, 12*cm]))

    return story, toc



# ---------------------------------------------------------------------------
# Content – Romanian
# ---------------------------------------------------------------------------

def content_ro(st, images=None):
    """
    Build the full Romanian document story with optional embedded chart images.

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
    story.append(H1("Cuprins", st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOCH1ro", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2ro", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3ro", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    story.append(toc)

    # =========================================================================
    # 1. Introducere
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("1  Ce este build_reports?", st))
    story.append(P(
        "build_reports este un instrument care creeaza automat diagrame relevante despre "
        "progresul si eficienta echipei tale agile. Ca date de intrare utilizeaza "
        "fisierele exportate de modulul <b>transform_data</b> din sistemul tau de "
        "gestionare a sarcinilor (de ex. Jira). "
        "build_reports citeste aceste fisiere si calculeaza mai multe <b>metrici de flux</b> "
        "— analize grafice care arata cat de rapid si cat de mult livreaza echipa ta.", st))
    story.append(P(
        "Programul dispune de o interfata grafica simpla (GUI): nu sunt necesare cunostinte "
        "de programare. La un simplu click, diagramele sunt afisate in browser sau salvate "
        "ca fisier PDF.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Prezentare generala a metricilor</b><br/>"
        "- <b>Flow Time / Cycle Time</b>: Cat timp dureaza finalizarea unui issue?<br/>"
        "- <b>Flow Velocity / Throughput</b>: Cate issues inchide echipa pe saptamana?<br/>"
        "- <b>Flow Load / WIP</b>: Cate issues sunt in lucru simultan?<br/>"
        "- <b>Cumulative Flow Diagram</b>: Cum evolueaza stocul in timp?<br/>"
        "- <b>Flow Distribution</b>: Cum sunt distribuite issues dupa tip, etapa si timp de ciclu?<br/>"
        "- <b>Process Flow: Transitions</b>: Ce trasee de stare parcurg issues? Unde apar reluari si bucle?<br/>"
        "- <b>Process Flow: Time</b>: Cat timp stationeaza issues in fiecare etapa? Ce tranzitii consuma cel mai mult timp?", st))

    # =========================================================================
    # 2. Cerinte preliminare
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Cerinte preliminare si instalare", st))

    story.append(H2("2.1  Ce trebuie instalat?", st))
    story.append(P(
        "build_reports este livrat ca un <b>pachet portabil</b>. Nu este necesara o "
        "instalare separata de Python.", st))
    story.append(BL(
        "<b>Windows:</b> Python 3.11 este deja inclus in pachet — dezarhiveaza si ruleaza.", st))
    story.append(BL(
        "<b>macOS / Linux:</b> La prima lansare, un mediu Python este configurat automat "
        "(aprox. 1 minut, necesita conexiune la internet). Ulterior aplicatia ruleaza "
        "offline.", st))

    story.append(H2("2.2  Pornirea programului", st))
    story.append(P(
        "Faceaza dublu-click pe lansatorul corespunzator din folderul extras:", st))
    story.append(BL(
        "<b>Windows:</b> Dublu-click pe <b>BuildReports.bat</b> — porneste interfata "
        "grafica fara fereastra de consola.", st))
    story.append(BL(
        "<b>macOS:</b> Click dreapta pe <b>BuildReports.command</b> → <i>Deschide</i> "
        "(o data, pentru a ocoli Gatekeeper).", st))
    story.append(BL(
        "<b>Linux:</b> Intr-un terminal: "
        "<font name='Courier'>./BuildReports.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Sfat (Windows):</b> La prima lansare, SmartScreen poate afisa un avertisment. "
        "Click pe <b>Mai multe informatii</b> → <b>Ruleaza oricum</b>.", st, "#e8f8f0"))

    # =========================================================================
    # 3. Fisiere de intrare
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("3  Fisiere de intrare", st))
    story.append(P(
        "build_reports necesita unul sau doua fisiere Excel generate de modulul "
        "<b>transform_data</b>. Aceste fisiere nu trebuie editate manual — "
        "structura trebuie sa corespunda exact formatului asteptat.", st))

    story.append(H2("3.1  IssueTimes.xlsx  (obligatoriu)", st))
    story.append(P(
        "Acest fisier contine toate issues (tichetele) impreuna cu datele de timp si "
        "starea curenta de procesare. Este necesar pentru toate metricile cu exceptia "
        "Diagramei de Flux Cumulativ.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coloana", "Semnificatie"],
        [
            ["Project",       "Cheia proiectului (de ex. ARTA)"],
            ["Key",           "Cheia issue-ului (de ex. ARTA-123)"],
            ["Issuetype",     "Tipul issue-ului (de ex. Feature, Bug, Story)"],
            ["Status",        "Starea curenta (de ex. In Progress, Done)"],
            ["Created",       "Data crearii issue-ului"],
            ["First Date",    "Data la care s-a lucrat activ prima data la issue"],
            ["Closed Date",   "Data finalizarii (goala = inca deschis)"],
            ["Resolution",    "Tipul de rezolutie (de ex. Fixed, Duplicate)"],
            ["Stage columns", "Cate o coloana per etapa de workflow cu minutele petrecute in acea etapa"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.2  CFD.xlsx  (optional, pentru Diagrama de Flux Cumulativ)", st))
    story.append(P(
        "Acest fisier contine numarul zilnic de intrari: cate issues au <b>intrat</b> "
        "intr-o etapa data in fiecare zi (nu instantanee). build_reports acumuleaza "
        "aceste valori intr-un total cumulat. Este necesar doar daca se doreste calculul "
        "Diagramei de Flux Cumulativ.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coloana", "Semnificatie"],
        [
            ["Day",           "Data (YYYY-MM-DD)"],
            ["Stage columns", "Cate o coloana per etapa cu numarul de intrari noi in ziua respectiva"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.3  Fisier de configurare PI  (optional, pentru Flow Velocity)", st))
    story.append(P(
        "Cu un fisier de configurare JSON optional poti defini propriile intervale PI "
        "(Program Increments) pentru diagrama cu bare a Flow Velocity. Fara acest fisier, "
        "se folosesc automat trimestrele calendaristice.", st))
    story.append(SP(4))
    story.append(P("<b>Exemplu (modul data):</b>", st))
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
        "Fisierul trebuie sa aiba extensia <b>.json</b>. Copiaza fisierul exemplu furnizat "
        "<b>pi_config_example.json</b> si ajusteaza datele si denumirile pentru a corespunde "
        "planificarii tale PI. Formatul trebuie pastrat.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> Foloseste intotdeauna formatul de data <b>YYYY-MM-DD</b> (an-luna-zi). "
        "Exemplu: 6 ianuarie 2025 = 2025-01-06.", st, "#fff8e1"))

    story.append(SP(8))
    story.append(H2("3.4  Transitions.xlsx  (optional, pentru Process Flow)", st))
    story.append(P(
        "Acest fisier contine toate tranzitiile de stare per issue in ordine cronologica. "
        "Este generat de modulul <b>transform_data</b> si este necesar exclusiv pentru "
        "<b>metrica Process Flow</b>. Toate celelalte metrici pot fi calculate fara "
        "acest fisier.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coloana", "Semnificatie"],
        [
            ["Key",        "Cheia issue-ului (de ex. ARTA-123)"],
            ["Transition", "Starea tinta dupa tranzitie (de ex. 'In Analysis')"],
            ["Timestamp",  "Marca de timp a tranzitiei (DD.MM.YYYY HH:MM:SS)"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> Transitions.xlsx si IssueTimes.xlsx trebuie sa provina din aceeasi "
        "executie de export transform_data, astfel incat cheile de issue sa corespunda.", st, "#fff8e1"))

    # =========================================================================
    # 4. Interfata grafica
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("4  Interfata grafica (GUI)", st))
    story.append(P(
        "Dupa pornire, se deschide fereastra principala. Aceasta consta din trei zone: "
        "zona <b>fisierelor</b> (sus), zona <b>filtrelor</b> (mijloc) si zona "
        "<b>actiunilor</b> (jos) cu fereastra de jurnal.", st))

    story.append(H2("4.1  Incarcarea fisierelor", st))
    story.append(P("Incarca mai intai fisierele necesare:", st))
    story.append(BL(
        "<b>IssueTimes</b> — Click pe butonul cu folder din dreapta campului si "
        "selecteaza fisierul <b>IssueTimes.xlsx</b>. Dupa incarcare, proiectele disponibile si "
        "tipurile de issue apar automat in jurnal.", st))
    story.append(BL(
        "<b>CFD (optional)</b> — Selecteaza fisierul <b>CFD.xlsx</b> daca ai nevoie de "
        "Diagrama de Flux Cumulativ.", st))
    story.append(BL(
        "<b>Workflow (optional)</b> — Selecteaza fisierul text de workflow din transform_data. "
        "Acesta contine marcatorii <b>&lt;First&gt;</b> si <b>&lt;Closed&gt;</b> care "
        "determina limitele de etapa marcate de liniile de tendinta CFD.", st))
    story.append(BL(
        "<b>PI config (optional)</b> — Selecteaza fisierul tau JSON de configurare pentru "
        "intervale PI personalizate. Lasa campul gol pentru a folosi trimestrele calendaristice.", st))
    story.append(BL(
        "<b>Transitions (optional)</b> — Selecteaza fisierul <b>Transitions.xlsx</b> din "
        "transform_data. Necesar doar daca se doreste calculul metricii Process Flow.",
        st))
    story.append(SP(4))
    story.append(box(
        "<b>Sfat:</b> Trecerea cursorului peste un camp de intrare afiseaza un tooltip care "
        "explica la ce este folosit campul.", st, "#e8f8f0"))

    story.append(H2("4.2  Setarea filtrelor", st))
    story.append(P(
        "Filtrele restrictioneaza ce issues sunt incluse in analiza:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Filtru / Excludere", "Descriere"],
        [
            ["De la / Pana la",
             "Considera doar issues inchise in acest interval de date. "
             "Format: YYYY-MM-DD. Butonul calendar deschide un selector de date."],
            ["Ultimele 365 de zile",
             "Seteaza automat De la si Pana la pentru ultimele 365 de zile pana azi."],
            ["Proiecte",
             "Analizeaza doar proiecte specifice. Separa mai multe proiecte cu virgula, "
             "de ex. ARTA, ARTB. Butonul de selectie afiseaza toate proiectele disponibile."],
            ["Tipuri de issue",
             "Analizeaza doar tipuri specifice de issue, de ex. Feature, Bug. "
             "Gol = toate tipurile. Butonul de selectie afiseaza o lista de selectie."],
            ["Excludere: Status",
             "Elimina complet din toate metricile issues cu anumite stari Jira, "
             "de ex. 'Canceled'. Butonul de selectie afiseaza toate starile existente."],
            ["Excludere: Resolution",
             "Exclude issues cu anumite tipuri de rezolutie, de ex. 'Won't Do' sau "
             "'Duplicate'. Butonul de selectie afiseaza toate rezolutiile existente."],
            ["Excludere issues zero-day",
             "Casuta de bifat: issues al caror timp de ciclu (First pana la Closed Date) este mai "
             "scurt decat pragul configurat sunt eliminate complet. Implicit: 5 minute. "
             "Tipic pentru issues care au fost parcurse manual prin workflow fara "
             "nicio activitate reala de dezvoltare."],
        ],
        col_widths=[3.8*cm, 12.2*cm]))

    story.append(H2("4.3  Selectarea metricilor si a metodei CT", st))
    story.append(P(
        "Foloseste casetele de bifat pentru a selecta ce metrici sa fie calculate. "
        "Butoanele <b>Toate</b> si <b>Nimic</b> seteaza sau deselecteaza toate casetele dintr-o data.",
        st))
    story.append(SP(4))
    story.append(P(
        "<b>Metoda CT</b> determina modul de calcul al timpului de ciclu — relevanta "
        "doar pentru metrica Flow Time:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Metoda", "Calcul"],
        [
            ["Metoda A (implicit)",
             "Diferenta in zile calendaristice intre First Date si Closed Date. "
             "Simpla si directa."],
            ["Metoda B",
             "Suma minutelor in etapele individuale de workflow (ultima etapa exclusa), "
             "impartita la 1440. Masoara doar timpul activ de procesare."],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(H2("4.4  Crearea unui raport", st))
    story.append(P("Ai doua optiuni:", st))
    story.append(BL(
        "<b>Afiseaza in browser</b> — Toate diagramele sunt deschise in browserul implicit. "
        "Diagramele sunt pe deplin interactive: mareste, examineaza punctele de date prin "
        "tooltip la hover si comuta categorii individuale in legenda.", st))
    story.append(BL(
        "<b>Exporta rapoarte</b> — Toate diagramele sunt exportate intr-un fisier PDF "
        "cu mai multe pagini. Un dialog de salvare solicita numele fisierului si locatia. "
        "Pe langa PDF, doua fisiere Excel sunt create automat: un Excel de raport cu toate "
        "issues, grupele de stare si timpii de ciclu, si — daca exista issues zero-day — "
        "un fisier separat pentru acele issues.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> In timp ce calculele ruleaza, interfata este blocata temporar. "
        "Progresul este afisat in fereastra de jurnal. Nu inchide si nu da click pana cand "
        "jurnalul nu afiseaza mesajul de finalizare.", st, "#fff8e1"))

    story.append(H2("4.5  Template-uri — salvarea si incarcarea configuratiei", st))
    story.append(P(
        "In meniul <b>Templates</b> poti salva toate setarile curente "
        "(cai de fisiere, filtre, selectie metrici, metoda CT, terminologie) ca fisier "
        "JSON si le poti reincarca ulterior — fara a completa din nou toate campurile.", st))
    story.append(BL(
        "<b>Salveaza...</b> — Alege o locatie si un nume pentru fisierul de configurare "
        "(de ex. echipaMea_RaportTrimestrial.json).", st))
    story.append(BL(
        "<b>Incarca...</b> — Deschide un fisier de configurare salvat. Toate campurile "
        "sunt completate automat. Daca un fisier salvat nu mai poate fi gasit, apare o "
        "nota in jurnal.", st))

    story.append(H2("4.6  Limba si terminologie", st))
    story.append(P(
        "Limba poate fi schimbata in doua moduri:", st))
    story.append(BL(
        "<b>Butonul cu steag</b> din coltul din dreapta sus al ferestrei — afiseaza "
        "limba curenta ca steag national. Un click comuta instant intre germana si "
        "engleza.", st))
    story.append(BL(
        "<b>Optiuni → Limba</b> — alternativ prin meniu.", st))
    story.append(P(
        "Prin <b>Optiuni → Terminologie</b> poti comuta intre <b>SAFe</b> si "
        "<b>Global</b>. In modul SAFe metricile se numesc de ex. 'Flow Time', in "
        "modul Global 'Cycle Time'. Aceasta comutare afecteaza doar etichetele, nu "
        "calculele.", st))

    # =========================================================================
    # 5. Metrici
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("5  Prezentare generala a metricilor", st))
    story.append(P(
        "Aceasta sectiune explica fiecare metrica in limbaj simplu: ce masoara, "
        "ce arata diagramele si cum se interpreteaza rezultatele. "
        "Diagramele exemplu se bazeaza pe un set de date demonstrativ.", st))

    # --- 5.1 Flow Time -------------------------------------------------------
    story.append(H2("5.1  Flow Time / Cycle Time", st))
    story.append(P(
        "<b>Ce se masoara?</b> Timpul de ciclu — adica numarul de zile pe care un issue "
        "il petrece de la prima activitate pana la finalizare. Mai scurt inseamna mai bine.", st))

    story.append(H3("Diagrama 1: Box plot (distributia)", st))
    story.append(P(
        "Box plot-ul arata dintr-o privire cum sunt distribuite timpii de ciclu. "
        "Antetul diagramei contine statisticile cheie:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Statistica", "Semnificatie"],
        [
            ["Min / Max",   "Cel mai scurt si cel mai lung timp de ciclu masurat"],
            ["Q1 / Q3",     "25% / 75% dintre issues se afla sub aceasta valoare"],
            ["Median",      "Timpul de ciclu median — 50% dintre issues se afla sub el"],
            ["Mean",        "Timpul de ciclu mediu (poate fi influentat de valori extreme)"],
            ["90d CT%",     "Ponderea issues cu timp de ciclu <= 90 de zile (Service Level Expectation)"],
            ["P85 / P95",   "85% / 95% dintre issues au fost finalizate in acest timp"],
            ["Std dev",     "Abaterea standard — cat variaza valorile?"],
            ["CV",          "Coeficientul de variatie — dispersia relativa (mai mic = proces mai stabil)"],
            ["Zero-Day",    "Numarul de issues cu timp de ciclu 0 (excluse din analiza)"],
        ],
        col_widths=[3*cm, 13*cm]))
    story.append(SP(4))
    story.append(HI(
        "Punct rosu in box plot = valoare statistica extrema. In browser poti citi "
        "cheia issue-ului prin tooltip la hover.", st))
    add_img("flow_time_box",
            "Fig. 1: Box plot al timpilor de ciclu — distributie, quartile si antet statistic.")

    story.append(H3("Diagrama 2: Scatter plot (tendinta in timp)", st))
    story.append(P(
        "Fiecare punct reprezinta un issue finalizat. Axa x afiseaza data finalizarii, "
        "axa y timpul de ciclu in zile. Culorile si liniile de referinta ajuta la "
        "interpretare:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Semnificatie"],
        [
            ["Punct albastru",  "Issues normale (sub percentila 85)"],
            ["Punct portocaliu","Issues lente (intre percentilele 85 si 95)"],
            ["Punct rosu",      "Issues foarte lente (peste percentila 95)"],
            ["Curba albastra",  "Linie de tendinta LOESS — arata tendinta timpului de ciclu in timp"],
            ["Linie rosie",     "Linie de referinta mediana"],
            ["Linie verde",     "Linie de referinta percentila 85"],
            ["Linie cian",      "Linie de referinta percentila 95"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_time_scatter",
            "Fig. 2: Scatter plot — timp de ciclu per data de finalizare cu linie de tendinta LOESS si linii de referinta.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretare:</b> Daca linia de tendinta LOESS urca spre dreapta, issues devin "
        "mai lente in timp. O linie plata semnaleaza un proces stabil. Multi puncte rosii si "
        "portocalii indica blocaje frecvente.", st))

    # --- 5.2 Flow Velocity ---------------------------------------------------
    story.append(H2("5.2  Flow Velocity / Throughput", st))
    story.append(P(
        "<b>Ce se masoara?</b> Throughput-ul — adica cate issues inchide echipa "
        "pe saptamana sau per PI. O viteza constant ridicata indica o echipa capabila "
        "de livrare.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Diagrama", "Afiseaza"],
        [
            ["Frecventa zilnica (histograma)",
             "De cate ori sunt inchise exact 1, 2, 3 ... issues intr-o singura zi. "
             "Arata productia zilnica tipica."],
            ["Tendinta saptamanala (diagrama linie)",
             "Numarul de issues inchise per saptamana de-a lungul intregii perioade. "
             "Fluctuatiile si tendintele devin imediat vizibile."],
            ["Tendinta PI (diagrama cu bare)",
             "Numarul de issues inchise per PI (Program Increment) sau trimestru. "
             "Linia rosie arata media. Culorile barelor: "
             "Gri = prima bara; Portocaliu = PI curent; Albastru = PI finalizate; "
             "Gri deschis = PI viitoare."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("velocity_daily",
            "Fig. 3: Frecventa zilnica — frecventa numarului de inchideri zilnice.")
    add_img("velocity_weekly",
            "Fig. 4: Tendinta saptamanala — issues inchise per saptamana calendaristica.")
    add_img("velocity_pi",
            "Fig. 5: Tendinta PI — issues inchise per PI sau trimestru cu linie de medie.")

    # --- 5.3 Flow Load -------------------------------------------------------
    story.append(H2("5.3  Flow Load / WIP  (Work in Progress)", st))
    story.append(P(
        "<b>Ce se masoara?</b> Cate issues sunt simultan in lucru si cat de vechi sunt "
        "deja. Prea multe issues paralele incetinesc livrarea "
        "(cu cat mai mult WIP, cu atat mai lung timpul de ciclu).", st))
    story.append(SP(4))
    story.append(P(
        "Diagrama afiseaza un box plot grupat: fiecare etapa primeste un box care arata "
        "varsta (in zile) a issues aflate acolo in prezent. Punctele individuale reprezinta "
        "issues individuale — in browser vezi cheia issue-ului la hover.", st))
    story.append(SP(4))
    story.append(P(
        "Liniile de referinta punctate din issues inchise (mediana, percentila 85, "
        "percentila 95) ofera orientare: issues care depasesc deja percentila 95 a issues "
        "inchise sunt semnificativ intarziate.", st))
    add_img("flow_load",
            "Fig. 6: Flow Load — varsta issues deschise per etapa cu linii de referinta din issues inchise.")

    # --- 5.4 CFD -------------------------------------------------------------
    story.append(H2("5.4  Diagrama de Flux Cumulativ (CFD)", st))
    story.append(P(
        "<b>Ce se masoara?</b> Cate issues in total au intrat in fiecare etapa — "
        "cumulate in timp, defalcate pe etape de workflow. Un sistem bine functional "
        "afiseaza benzi paralele, cu crestere uniforma, fara umflare in etape individuale.", st))
    story.append(SP(4))
    story.append(P(
        "Diagrama este o diagrama de suprafata stivuita: fiecare strat colorat corespunde "
        "unei etape. Prima etapa este sus, ultima (Done/Closed) jos. "
        "Diagrama incepe intotdeauna de la 0 — indiferent de data de inceput selectata. "
        "Doua linii de tendinta negre arata:", st))
    story.append(BL(
        "<b>Linia superioara (intrare):</b> Merge de-a lungul marginii vizuale superioare a "
        "etapei &lt;First&gt; (intrarea in sistem). Fara fisier workflow: prima etapa.", st))
    story.append(BL(
        "<b>Linia inferioara (iesire):</b> Merge de-a lungul marginii vizuale superioare a "
        "etapei &lt;Closed&gt; (finalizarea in sistem). Fara fisier workflow: ultima etapa.",
        st))
    add_img("cfd",
            "Fig. 7: Diagrama de Flux Cumulativ — intrari cumulate per etapa cu linii de tendinta de intrare si iesire.")
    story.append(SP(4))
    story.append(P(
        "Raportul <b>In/Out</b> din titlul diagramei (de ex. 'Ratio In/out 1.80 : 1') "
        "arata daca intra mai mult decat se finalizeaza. O valoare de 1.0 inseamna un "
        "sistem echilibrat; valori semnificativ peste 1.0 indica un backlog in crestere.",
        st))
    story.append(SP(4))
    story.append(P(
        "Axa x afiseaza limitele de luna cu etichete mari (de ex. 'Ian 2025') si "
        "saptamanile calendaristice ISO cu etichete mici gri (de ex. 'S03'), astfel incat "
        "etichetele sa nu se suprapuna.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> CFD necesita fisierul optional CFD.xlsx. Fara acest fisier "
        "metrica CFD nu poate fi calculata.", st, "#fff8e1"))

    # --- 5.5 Flow Distribution -----------------------------------------------
    story.append(H2("5.5  Flow Distribution", st))
    story.append(P(
        "<b>Ce se masoara?</b> Compozitia tuturor issues dupa tip, etapa dominanta "
        "si timp de ciclu mediu. Arata dintr-o privire ce tipuri de issue domina, "
        "unde issues petrec cel mai mult timp si ce tipuri sunt procesate cel mai rapid "
        "sau cel mai lent.", st))
    story.append(SP(4))
    story.append(P(
        "Diagrama consta din trei subdiagrame alaturate:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Diagrama", "Ce se afiseaza?"],
        [
            ["Dupa tip de issue (donut)",
             "Numar si pondere procentuala a issues per tip de issue. Toate issues sunt incluse."],
            ["Stage Prominence (donut)",
             "Pentru fiecare issue se identifica etapa in care a petrecut cel mai mult timp. "
             "Diagrama numara de cate ori fiecare etapa a fost dominanta pentru toate issues. "
             "Pentru issues inchise, etapa terminala Done (starea curenta) este exclusa, "
             "astfel incat timpul de asteptare dupa inchidere sa nu distorsioneze rezultatul. "
             "Subtitrarea afiseaza numarul de issues contributoare (n=...). "
             "Issues fara date de etapa nu sunt numarate."],
            ["Timp de ciclu mediu dupa tip (bare)",
             "Timp de ciclu mediu in zile per tip de issue (Metoda A: "
             "Closed Date - First Date). Sunt incluse doar issues cu ambele campuri de data si "
             "CT > 0. Etichetele barelor in formatul '15.0d'."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_dist",
            "Fig. 8: Flow Distribution — distributia tipurilor de issue, Stage Prominence si timp de ciclu mediu per tip.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretare Stage Prominence:</b> Daca o etapa domina in mod deosebit de "
        "frecvent, issues stationeaza acolo disproportionat de mult — un potential blocaj in "
        "workflow. Issues inchise sunt incluse, dar etapa lor terminala Done este "
        "ascunsa, astfel incat blocajele reale de procesare raman vizibile.", st))

    # --- 5.6 Process Flow: Transitions ----------------------------------------
    story.append(H2("5.6  Process Flow: Transitions", st))
    story.append(P(
        "<b>Ce se masoara?</b> Toate tranzitiile de stare ale issues sunt vizualizate ca un "
        "graf directionat: noduri = stari, sageti = tranzitii. Grosimea sagetii este "
        "proportionala cu frecventa tranzitiei. Astfel devine imediat clar ce trasee parcurg "
        "issues prin workflow, cat de des apar reluari si unde issues se blocheaza in bucle.", st))
    story.append(SP(4))
    story.append(P(
        "Aceasta metrica necesita fisierul optional <b>Transitions.xlsx</b> (din "
        "transform_data). Fara acest fisier apare un avertisment in jurnal.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Semnificatie"],
        [
            ["Sageata albastra",    "Tranzitie inainte — issue avanseaza in workflow."],
            ["Sageata rosie",       "Tranzitie inapoi (reluare) — issue revine la o etapa anterioara."],
            ["Arc portocaliu",      "Bucla proprie — issue ramane in acelasi status (de ex. etapa parcursa din nou)."],
            ["Grosimea sagetii",    "Cu cat sageata e mai groasa, cu atat tranzitia este mai frecventa."],
            ["Numar pe sageata",    "Numarul absolut al acestei tranzitii pentru toate issues."],
            ["Nod",                 "Cerc albastru inchis cu numele starii. Ordine: etapele workflow mai intai "
                                    "(in sensul acelor de ceasornic), apoi stari suplimentare alfabetic."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow",
            "Fig. 9: Process Flow: Transitions — graf directionat al tuturor tranzitiilor de stare cu grosimea si codificarea de culoare a muchiilor.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretare:</b> Multe sageti rosii inseamna reluari frecvente — semn al unor "
        "probleme de calitate sau cerinte neclare. Sagetile albastre groase arata traseul "
        "principal de workflow. Buclele proprii (portocaliu) apar cand un issue este setat "
        "de mai multe ori in acelasi status.", st))

    # --- 5.7 Process Flow: Time -----------------------------------------------
    story.append(H2("5.7  Process Flow: Time", st))
    story.append(P(
        "<b>Ce se masoara?</b> Acelasi graf directionat ca Process Flow: Transitions, "
        "dar cu accent pe <b>timp</b>: latimea nodului si etichetele muchiilor se bazeaza pe "
        "timpul median de stationare al etapei sursa. Astfel devine imediat vizibil in "
        "care etape issues asteapta cel mai mult si care tranzitii consuma cel mai mult timp.", st))
    story.append(SP(4))
    story.append(P(
        "Aceasta metrica necesita de asemenea fisierul optional <b>Transitions.xlsx</b> "
        "(din transform_data).", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Semnificatie"],
        [
            ["Latimea nodului",      "Proportionala cu timpul median de stationare in aceasta etapa."],
            ["Grosimea muchiei",     "Proportionala cu timpul median de stationare al etapei sursa."],
            ["Numar pe sageata",     "Timpul median de stationare al etapei sursa in zile (z) pentru issues care au urmat exact aceasta tranzitie."],
            ["Sageata albastra",     "Tranzitie inainte."],
            ["Sageata rosie",        "Tranzitie inapoi (reluare)."],
            ["Arc portocaliu",       "Bucla proprie."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow_time",
            "Fig. 10: Process Flow: Time — latimea nodului si etichetele muchiilor bazate pe timpul median de stationare per etapa.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretare:</b> Noduri late si muchii groase indica etape unde issues "
        "stationeaza deosebit de mult — potentiale blocaje. Comparativ cu Process Flow: "
        "Transitions, poti vedea daca tranzitiile frecvente au si o pondere semnificativa "
        "de timp sau sunt doar schimbari rapide de stare.", st))

    # =========================================================================
    # 6. Export PDF
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("6  Export PDF", st))
    story.append(P(
        "Exportul PDF creeaza un fisier PDF cu mai multe pagini cu toate diagramele selectate. "
        "Fiecare diagrama apare pe propria pagina.", st))
    story.append(SP(6))
    story.append(tbl(
        ["Pas", "Actiune"],
        [
            ["1", "Incarca fisierele si seteaza filtrele (asa cum este descris in Capitolul 4)."],
            ["2", "Selecteaza metricile dorite prin casete de bifat."],
            ["3", "Click pe 'Exporta rapoarte'."],
            ["4", "In dialogul de salvare, alege un nume de fisier si o locatie si confirma."],
            ["5", "Programul calculeaza si exporta; progresul apare in jurnal."],
            ["6", "Dupa finalizare, PDF-ul si Excel-ul de raport sunt disponibile la locatia aleasa."],
        ],
        col_widths=[1.5*cm, 14.5*cm]))
    story.append(SP(8))
    story.append(H2("6.1  Excel de raport automat", st))
    story.append(P(
        "La fiecare export PDF un fisier Excel cu acelasi nume este creat automat "
        "(de ex. raport.xlsx langa raport.pdf). Acest fisier contine toate issues "
        "filtrate in formatul IssueTimes, completat cu trei coloane:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coloana", "Continut"],
        [
            ["Status Group",
             "Grupa de stare a issue-ului: 'To Do' (neinceputa), "
             "'In Progress' (in lucru) sau 'Done' (finalizata). "
             "Derivata din First Date si Closed Date."],
            ["Cycle Time (First->Closed)",
             "Timp de ciclu in zile calendaristice de la First Date la Closed Date "
             "(Metoda A). Gol daca lipseste oricare data."],
            ["Cycle Time B (days in Status)",
             "Suma minutelor in toate etapele de workflow exceptand ultima, "
             "impartita la 1440 (Metoda B). Gol daca lipseste oricare data."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(SP(8))
    story.append(box(
        "<b>Issues zero-day:</b> Doua mecanisme functioneaza independent:<br/>"
        "1. <b>Filtru de excludere (inainte de calcul):</b> Daca caseta de bifat "
        "'Excludere issues zero-day' este activa, issues cu un timp de ciclu sub pragul "
        "configurat (implicit: 5 minute) sunt eliminate complet din toate metricile.<br/>"
        "2. <b>In cadrul metricii Flow Time:</b> Issues cu timp de ciclu de 0 zile "
        "(aceeasi zi calendaristica) sunt raportate separat si nu sunt incluse in "
        "statistici.<br/>"
        "In ambele cazuri un fisier Excel separat este creat "
        "(de ex. raport_issues_zero_day.xlsx in acelasi folder).", st,
        "#fff8e1"))

    # =========================================================================
    # 7. Intrebari frecvente
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("7  Intrebari frecvente", st))

    faqs = [
        (
            "Diagramele nu apar in browser.",
            "Verifica daca este configurat un browser implicit. Incearca alternativ exportul "
            "PDF. Asigura-te ca fisierul IssueTimes a fost incarcat corect (verifica jurnalul)."
        ),
        (
            "Exportul PDF dureaza foarte mult sau esueaza.",
            "Randarea diagramelor ca PDF necesita pachetul Kaleido. Daca acesta nu a fost "
            "inca configurat, contacteaza persoana tehnica responsabila."
        ),
        (
            "Jurnalul afiseaza 'Stage only in IssueTimes' sau 'Stage only in CFD'.",
            "Coloanele de etapa din IssueTimes.xlsx si CFD.xlsx nu corespund. Acesta este un "
            "avertisment care nu opreste analiza, dar indica faptul ca fisierele provin "
            "din versiuni diferite de workflow."
        ),
        (
            "Cum pot analiza doar un anumit proiect?",
            "Introdu cheia proiectului dorit in campul 'Proiecte' (de ex. ARTA). "
            "Separa mai multe proiecte cu virgula. Alternativ: foloseste butonul de selectie "
            "pentru o lista a tuturor proiectelor disponibile."
        ),
        (
            "Diagrama de Flux Cumulativ nu apare.",
            "Metrica CFD necesita un fisier CFD.xlsx. Incarca-l in campul 'CFD (optional)'."
        ),
        (
            "Process Flow afiseaza 'No transition data available'.",
            "Metrica Process Flow necesita un fisier Transitions.xlsx din transform_data. "
            "Incarca-l in campul 'Transitions (optional)'. Asigura-te ca fisierul provine din "
            "aceeasi executie de export ca IssueTimes.xlsx."
        ),
        (
            "Care este diferenta dintre intervalele PI si trimestre?",
            "In mod implicit, trimestrele calendaristice (T1-T4) sunt folosite ca intervale "
            "de timp. Cu un fisier de configurare PI poti defini propriile intervale care "
            "corespund PI-urilor tale reale — de exemplu daca PI-ul tau incepe pe 6 ianuarie "
            "in loc de 1 ianuarie."
        ),
        (
            "Cum imi salvez setarile?",
            "Foloseste meniul 'Templates' -> 'Salveaza...' pentru a salva toate setarile "
            "curente intr-un fisier JSON. Data viitoare: 'Templates' -> 'Incarca...'. "
            "Setarile de excludere pot fi stocate permanent suplimentar sub "
            "'Templates' -> 'Salveaza excluderile ca implicit'."
        ),
        (
            "Un issue apare in metrici desi nu s-a lucrat niciodata cu adevarat la el.",
            "Acest lucru se intampla cand un issue a fost parcurs manual prin toate etapele "
            "de workflow in cateva secunde — fara nicio activitate reala de dezvoltare. "
            "Activeaza caseta de bifat 'Excludere issues zero-day' la 'Excluderi' in GUI "
            "(prag de ex. 5 minute). Issue-ul este eliminat complet din toate metricile si "
            "documentat intr-un fisier Excel separat."
        ),
        (
            "Pot prezenta rezultatele fara calculator?",
            "Da: exporteaza mai intai un raport PDF. Fisierul PDF contine toate diagramele "
            "si poate fi deschis pe orice dispozitiv. Pentru prezentari interactive, "
            "se recomanda vizualizarea in browser."
        ),
    ]
    for q, a in faqs:
        story.append(H3("I: " + q, st))
        story.append(P("R: " + a, st))
        story.append(SP(4))

    # =========================================================================
    # 8. Glosar
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("8  Glosar", st))
    story.append(tbl(
        ["Termen", "Explicatie"],
        [
            ["Closed Date",    "Data la care un issue a fost finalizat."],
            ["Cycle Time",     "Termen alternativ pentru Flow Time (terminologie globala)."],
            ["First Date",     "Data primei activitati active la un issue."],
            ["Flow Load",      "Numarul de issues aflate in prezent in lucru (termen SAFe)."],
            ["Flow Time",      "Timp de ciclu de la prima activitate pana la finalizare."],
            ["Flow Velocity",  "Numarul de issues finalizate pe unitate de timp (termen SAFe)."],
            ["Issue",          "Un tichet in sistemul de gestionare a sarcinilor (de ex. un card Jira)."],
            ["Issue type",     "Categoria unui issue, de ex. Feature, Bug, Story, Task."],
            ["IssueTimes",     "Fisierul Excel cu toate issues generat de transform_data."],
            ["JSON",           "Format text simplu pentru fisierele de configurare."],
            ["LOESS",          "Metoda statistica de netezire pentru liniile de tendinta."],
            ["P85 / P95",      "Percentila 85 / 95 a timpilor de ciclu."],
            ["PI",             "Program Increment — o perioada fixa de planificare si livrare."],
            ["Process Flow: Transitions", "Graf directionat al tuturor tranzitiilor de stare (bazat pe frecventa). Arata traseele principale, reluarile si buclele in workflow."],
            ["Process Flow: Time",        "Graf directionat al tuturor tranzitiilor de stare (bazat pe timp). Latimea nodului si etichetele muchiilor arata timpul median de stationare per etapa."],
            ["Resolution",     "Tipul de rezolutie al unui issue, de ex. 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework — un framework pentru scalare agila."],
            ["Stage",          "Un pas in workflow, de ex. Analiza, Implementare, Done."],
            ["Template",       "Fisier de configurare salvat cu toate setarile."],
            ["Throughput",     "Termen alternativ pentru Flow Velocity (terminologie globala)."],
            ["Transitions",    "Inregistrarea fiecarei schimbari de stare per issue. Exportat de transform_data ca Transitions.xlsx."],
            ["WIP",            "Work in Progress — issues aflate in prezent in lucru."],
            ["Zero-day issue", "Un issue al carui timp de ciclu (First pana la Closed Date) este atat de scurt "
                               "incat nu reprezinta un timp real de procesare. De obicei cauzat de "
                               "parcurgerea manuala a workflow-ului. Poate fi eliminat din "
                               "toate metricile printr-un filtru de prag."],
        ],
        col_widths=[4*cm, 12*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content – Portuguese
# ---------------------------------------------------------------------------

def content_pt(st, images=None):
    """
    Build the full Portuguese document story with optional embedded chart images.

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
    story.append(H1("Conteudo", st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOCH1pt", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2pt", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3pt", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    story.append(toc)

    # =========================================================================
    # 1. Introducao
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("1  O que e o build_reports?", st))
    story.append(P(
        "build_reports e uma ferramenta que cria automaticamente graficos significativos sobre "
        "o progresso e a eficiencia da sua equipa agil. Como entrada, utiliza os dados que o "
        "modulo <b>transform_data</b> exportou do seu sistema de tickets (por exemplo, Jira). "
        "build_reports le estes ficheiros e calcula varias <b>metricas de fluxo</b> -- "
        "analises graficas que mostram quao rapida e eficiente e a entrega da equipa.", st))
    story.append(P(
        "O programa tem uma interface grafica simples (GUI): nao sao necessarios "
        "conhecimentos de programacao. Com um clique, os graficos sao apresentados no "
        "navegador ou guardados como ficheiro PDF.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Resumo das metricas</b><br/>"
        "- <b>Flow Time / Cycle Time</b>: Quanto tempo demora um issue a ser concluido?<br/>"
        "- <b>Flow Velocity / Throughput</b>: Quantos issues a equipa fecha por semana?<br/>"
        "- <b>Flow Load / WIP</b>: Quantos issues estao em curso simultaneamente?<br/>"
        "- <b>Cumulative Flow Diagram</b>: Como evolui o inventario ao longo do tempo?<br/>"
        "- <b>Flow Distribution</b>: Como se distribuem os issues por tipos, etapas e tempos de ciclo?<br/>"
        "- <b>Process Flow: Transitions</b>: Que caminhos de status percorrem os issues? Onde ocorrem retrabalhos e ciclos?<br/>"
        "- <b>Process Flow: Time</b>: Quanto tempo permanecem os issues em cada etapa? Que transicoes custam mais tempo?", st))

    # =========================================================================
    # 2. Requisitos
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Requisitos e instalacao", st))

    story.append(H2("2.1  O que precisa de ser instalado?", st))
    story.append(P(
        "build_reports e fornecido como um <b>pacote portatil</b>. Nao e necessaria uma "
        "instalacao Python separada.", st))
    story.append(BL(
        "<b>Windows:</b> O Python 3.11 ja esta incluido no pacote -- basta descompactar "
        "e iniciar.", st))
    story.append(BL(
        "<b>macOS / Linux:</b> No primeiro arranque, um ambiente Python e configurado "
        "automaticamente (aprox. 1 minuto, internet necessaria). Apos isso, a aplicacao "
        "funciona sem ligacao a internet.", st))

    story.append(H2("2.2  Iniciar o programa", st))
    story.append(P(
        "Faca duplo clique no iniciador adequado na pasta extraida:", st))
    story.append(BL(
        "<b>Windows:</b> Duplo clique em <b>BuildReports.bat</b> -- inicia a GUI "
        "sem janela de consola.", st))
    story.append(BL(
        "<b>macOS:</b> Clique com o botao direito em <b>BuildReports.command</b> → <i>Abrir</i> "
        "(uma vez, para contornar o Gatekeeper).", st))
    story.append(BL(
        "<b>Linux:</b> Num terminal: "
        "<font name='Courier'>./BuildReports.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Dica (Windows):</b> No primeiro arranque, o SmartScreen pode mostrar um aviso. "
        "Clique em <b>Mais informacoes</b> → <b>Executar mesmo assim</b>.", st, "#e8f8f0"))

    # =========================================================================
    # 3. Ficheiros de entrada
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("3  Ficheiros de entrada", st))
    story.append(P(
        "build_reports requer um ou dois ficheiros Excel produzidos pelo modulo "
        "<b>transform_data</b>. Estes ficheiros nao devem ser editados manualmente -- "
        "a estrutura tem de corresponder exatamente ao formato esperado.", st))

    story.append(H2("3.1  IssueTimes.xlsx  (obrigatorio)", st))
    story.append(P(
        "Este ficheiro contem todos os issues (tickets) com os respetivos dados de tempo "
        "e estado de processamento atual. E necessario para todas as metricas, exceto o "
        "Cumulative Flow Diagram.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coluna", "Significado"],
        [
            ["Project",       "Chave do projeto (por exemplo, ARTA)"],
            ["Key",           "Chave do issue (por exemplo, ARTA-123)"],
            ["Issuetype",     "Tipo de issue (por exemplo, Feature, Bug, Story)"],
            ["Status",        "Estado atual (por exemplo, In Progress, Done)"],
            ["Created",       "Data de criacao do issue"],
            ["First Date",    "Data em que o issue foi trabalhado pela primeira vez ativamente"],
            ["Closed Date",   "Data de conclusao (vazio = ainda em aberto)"],
            ["Resolution",    "Tipo de resolucao (por exemplo, Fixed, Duplicate)"],
            ["Stage columns", "Uma coluna por etapa do fluxo com os minutos passados nessa etapa"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.2  CFD.xlsx  (opcional, para o Cumulative Flow Diagram)", st))
    story.append(P(
        "Este ficheiro contem contagens diarias de entradas: quantos issues <b>entraram</b> "
        "numa determinada etapa em cada dia (nao instantaneos). build_reports acumula estes "
        "valores num total progressivo. So e necessario se o Cumulative Flow Diagram for "
        "calculado.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coluna", "Significado"],
        [
            ["Day",           "Data (AAAA-MM-DD)"],
            ["Stage columns", "Uma coluna por etapa com o numero de novas entradas nesse dia"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.3  Ficheiro de configuracao PI  (opcional, para Flow Velocity)", st))
    story.append(P(
        "Com um ficheiro de configuracao JSON opcional pode definir os seus proprios "
        "intervalos PI (Program Increments) para o grafico de barras Flow Velocity. "
        "Sem este ficheiro, sao utilizados automaticamente os trimestres do calendario.", st))
    story.append(SP(4))
    story.append(P("<b>Exemplo (modo data):</b>", st))
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
        "O ficheiro tem de ter a extensao <b>.json</b>. Copie o ficheiro de exemplo "
        "<b>pi_config_example.json</b> fornecido e ajuste as datas e os nomes ao seu "
        "calendario de PIs. O formato tem de ser preservado.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> Utilize sempre o formato de data <b>AAAA-MM-DD</b> (ano-mes-dia). "
        "Exemplo: 6 de janeiro de 2025 = 2025-01-06.", st, "#fff8e1"))

    story.append(SP(8))
    story.append(H2("3.4  Transitions.xlsx  (opcional, para Process Flow)", st))
    story.append(P(
        "Este ficheiro contem todas as transicoes de estado por issue em ordem cronologica. "
        "E produzido pelo modulo <b>transform_data</b> e e necessario exclusivamente "
        "para a <b>metrica Process Flow</b>. Todas as outras metricas podem ser calculadas "
        "sem este ficheiro.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coluna", "Significado"],
        [
            ["Key",        "Chave do issue (por exemplo, ARTA-123)"],
            ["Transition", "Estado de destino apos a transicao (por exemplo, 'In Analysis')"],
            ["Timestamp",  "Data e hora da transicao (DD.MM.AAAA HH:MM:SS)"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> Transitions.xlsx e IssueTimes.xlsx devem provir da mesma execucao "
        "de exportacao do transform_data, para que as chaves dos issues correspondam.", st, "#fff8e1"))

    # =========================================================================
    # 4. GUI
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("4  A Interface Grafica (GUI)", st))
    story.append(P(
        "Apos o arranque, abre-se a janela principal. E composta por tres areas: "
        "a <b>area de ficheiros</b> (em cima), a <b>area de filtros</b> (ao centro) e "
        "a <b>area de acoes</b> (em baixo) com a janela de registo.", st))

    story.append(H2("4.1  Carregar ficheiros", st))
    story.append(P("Carregue primeiro os ficheiros necessarios:", st))
    story.append(BL(
        "<b>IssueTimes</b> -- Clique no botao de pasta a direita do campo e selecione "
        "o ficheiro <b>IssueTimes.xlsx</b>. Apos o carregamento, os projetos e tipos "
        "de issue disponiveis aparecem automaticamente no registo.", st))
    story.append(BL(
        "<b>CFD (opcional)</b> -- Selecione o ficheiro <b>CFD.xlsx</b> se necessitar "
        "do Cumulative Flow Diagram.", st))
    story.append(BL(
        "<b>Workflow (opcional)</b> -- Selecione o ficheiro de texto do fluxo do "
        "transform_data. Contem os marcadores <b>&lt;First&gt;</b> e <b>&lt;Closed&gt;</b> "
        "que determinam quais os limites de etapa assinalados pelas linhas de tendencia do CFD.", st))
    story.append(BL(
        "<b>Config PI (opcional)</b> -- Selecione o seu ficheiro de configuracao JSON "
        "para intervalos PI personalizados. Deixe o campo vazio para usar trimestres do calendario.", st))
    story.append(BL(
        "<b>Transitions (opcional)</b> -- Selecione o ficheiro <b>Transitions.xlsx</b> do "
        "transform_data. So e necessario se a metrica Process Flow for calculada.",
        st))
    story.append(SP(4))
    story.append(box(
        "<b>Dica:</b> Pairar o rato sobre um campo de entrada mostra uma dica de contexto "
        "a explicar para que serve esse campo.", st, "#e8f8f0"))

    story.append(H2("4.2  Definir filtros", st))
    story.append(P(
        "Os filtros restringem quais os issues incluidos na analise:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Filtro / Exclusao", "Descricao"],
        [
            ["De / Ate",
             "Considerar apenas issues fechados neste intervalo de datas. "
             "Formato: AAAA-MM-DD. O botao de calendario abre um seletor de datas."],
            ["Ultimos 365 dias",
             "Define automaticamente De e Ate para os ultimos 365 dias ate hoje."],
            ["Projetos",
             "Analisar apenas projetos especificos. Separe varios projetos com virgula, "
             "por exemplo ARTA, ARTB. O botao de selecao mostra todos os projetos disponiveis."],
            ["Tipos de issue",
             "Analisar apenas tipos de issue especificos, por exemplo Feature, Bug. "
             "Vazio = todos os tipos. O botao de selecao mostra uma lista de escolha."],
            ["Excluir: Estado",
             "Remover completamente issues com determinados estados Jira de todas as metricas, "
             "por exemplo 'Canceled'. O botao de selecao mostra todos os estados existentes."],
            ["Excluir: Resolucao",
             "Excluir issues com determinados tipos de resolucao, por exemplo 'Won't Do' ou "
             "'Duplicate'. O botao de selecao mostra todas as resolucoes existentes."],
            ["Excluir issues zero-day",
             "Caixa de selecao: issues cujo tempo de ciclo (First to Closed Date) seja inferior "
             "ao limiar configurado sao completamente removidos. Padrao: 5 minutos. "
             "Tipico de issues que foram clicados manualmente pelo fluxo sem qualquer "
             "trabalho de desenvolvimento real."],
        ],
        col_widths=[3.8*cm, 12.2*cm]))

    story.append(H2("4.3  Selecionar metricas e metodo CT", st))
    story.append(P(
        "Utilize as caixas de selecao para escolher quais as metricas a calcular. "
        "Os botoes <b>Todas</b> e <b>Nenhuma</b> ativam ou desativam todas as caixas de uma vez.",
        st))
    story.append(SP(4))
    story.append(P(
        "O <b>metodo CT</b> determina como e calculado o tempo de ciclo -- relevante "
        "apenas para a metrica Flow Time:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Metodo", "Calculo"],
        [
            ["Metodo A (padrao)",
             "Diferenca em dias de calendario entre First Date e Closed Date. "
             "Simples e direto."],
            ["Metodo B",
             "Soma de minutos nas etapas individuais do fluxo (excluindo a ultima etapa), "
             "dividida por 1440. Mede apenas o tempo de processamento ativo."],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(H2("4.4  Criar um relatorio", st))
    story.append(P("Tem duas opcoes:", st))
    story.append(BL(
        "<b>Mostrar no navegador</b> -- Todos os graficos sao abertos no seu navegador "
        "predefinido. Os graficos sao totalmente interativos: ampliar, inspecionar pontos "
        "de dados com o cursor e ativar/desativar categorias individuais na legenda.", st))
    story.append(BL(
        "<b>Exportar relatorios</b> -- Todos os graficos sao exportados para um ficheiro "
        "PDF de multiplas paginas. Uma caixa de dialogo pede o nome e o local do ficheiro. "
        "Para alem do PDF, sao criados automaticamente dois ficheiros Excel: um Excel de "
        "relatorio com todos os issues, grupos de estado e tempos de ciclo, e -- se existirem "
        "issues zero-day -- um ficheiro separado para esses issues.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> Enquanto os calculos estao em curso, a interface fica brevemente "
        "bloqueada. O progresso e apresentado na janela de registo. Nao feche nem clique "
        "ate o registo mostrar a mensagem de conclusao.", st, "#fff8e1"))

    story.append(H2("4.5  Templates -- guardar e carregar configuracao", st))
    story.append(P(
        "No menu <b>Templates</b> pode guardar todas as definicoes atuais "
        "(caminhos de ficheiros, filtros, selecao de metricas, metodo CT, terminologia) "
        "como ficheiro JSON e recarrega-las mais tarde -- sem necessidade de preencher "
        "todos os campos de novo.", st))
    story.append(BL(
        "<b>Guardar...</b> -- Escolha um local e um nome para o ficheiro de configuracao "
        "(por exemplo myEquipa_RelatorioTrimestral.json).", st))
    story.append(BL(
        "<b>Carregar...</b> -- Abra um ficheiro de configuracao guardado. Todos os campos "
        "sao preenchidos automaticamente. Se um ficheiro guardado ja nao puder ser "
        "encontrado, aparece uma nota no registo.", st))

    story.append(H2("4.6  Idioma e terminologia", st))
    story.append(P(
        "O idioma pode ser alterado de duas formas:", st))
    story.append(BL(
        "<b>Botao de bandeira</b> no canto superior direito da janela -- mostra o idioma "
        "atual como bandeira nacional. Um clique alterna imediatamente entre alemao e "
        "ingles.", st))
    story.append(BL(
        "<b>Opcoes → Idioma</b> menu -- alternativamente atraves do menu.", st))
    story.append(P(
        "Via <b>Opcoes → Terminologia</b> tambem pode alternar entre <b>SAFe</b> e "
        "<b>Global</b>. No modo SAFe as metricas chamam-se por exemplo 'Flow Time', no "
        "modo Global 'Cycle Time'. Esta alteracao afeta apenas as etiquetas, nao os "
        "calculos.", st))

    # =========================================================================
    # 5. Metricas
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("5  Visao geral das metricas", st))
    story.append(P(
        "Esta seccao explica cada metrica em linguagem simples: o que mede, "
        "o que os graficos mostram e como interpretar os resultados. "
        "Os graficos de exemplo baseiam-se num conjunto de dados de amostra.", st))

    # --- 5.1 Flow Time -------------------------------------------------------
    story.append(H2("5.1  Flow Time / Cycle Time", st))
    story.append(P(
        "<b>O que e medido?</b> O tempo de ciclo -- ou seja, o numero de dias que um "
        "issue demora desde o inicio do trabalho ate a conclusao. Quanto menor, melhor.", st))

    story.append(H3("Grafico 1: Box plot (distribuicao)", st))
    story.append(P(
        "O box plot mostra de imediato como se distribuem os tempos de ciclo. "
        "O cabecalho do grafico contem as principais estatisticas:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Estatistica", "Significado"],
        [
            ["Min / Max",   "Tempo de ciclo mais curto e mais longo medido"],
            ["Q1 / Q3",     "25% / 75% dos issues ficam abaixo deste valor"],
            ["Mediana",     "O tempo de ciclo mediano -- 50% dos issues ficam abaixo dele"],
            ["Media",       "Tempo de ciclo medio (pode ser distorcido por valores extremos)"],
            ["90d CT%",     "Percentagem de issues com tempo de ciclo <= 90 dias (Service Level Expectation)"],
            ["P85 / P95",   "85% / 95% dos issues foram concluidos dentro deste prazo"],
            ["Desvio pad.",  "Desvio padrao -- quanta variacao existe nos valores?"],
            ["CV",          "Coeficiente de variacao -- dispersao relativa (menor = processo mais estavel)"],
            ["Zero-Day",    "Numero de issues com tempo de ciclo 0 (excluidos da analise)"],
        ],
        col_widths=[3*cm, 13*cm]))
    story.append(SP(4))
    story.append(HI(
        "Ponto vermelho no box plot = valor extremo estatistico. No navegador pode ler "
        "a chave do issue com o cursor.", st))
    add_img("flow_time_box",
            "Fig. 1: Box plot dos tempos de ciclo -- distribuicao, quartis e cabecalho de estatisticas.")

    story.append(H3("Grafico 2: Scatter plot (tendencia ao longo do tempo)", st))
    story.append(P(
        "Cada ponto e um issue concluido. O eixo x mostra a data de conclusao, "
        "o eixo y o tempo de ciclo em dias. As cores e linhas de referencia facilitam "
        "a interpretacao:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Elemento", "Significado"],
        [
            ["Ponto azul",    "Issues normais (abaixo do percentil 85)"],
            ["Ponto laranja", "Issues lentos (entre o percentil 85 e o percentil 95)"],
            ["Ponto vermelho","Issues muito lentos (acima do percentil 95)"],
            ["Curva azul",    "Linha de tendencia LOESS -- mostra a tendencia do tempo de ciclo ao longo do tempo"],
            ["Linha vermelha","Linha de referencia da mediana"],
            ["Linha verde",   "Linha de referencia do percentil 85"],
            ["Linha ciana",   "Linha de referencia do percentil 95"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_time_scatter",
            "Fig. 2: Scatter plot -- tempo de ciclo por data de conclusao com linha de tendencia LOESS e linhas de referencia.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretacao:</b> Se a linha de tendencia LOESS subir para a direita, os issues "
        "estao a ficar mais lentos ao longo do tempo. Uma linha plana indica um processo "
        "estavel. Muitos pontos vermelhos e laranja indicam estrangulamentos frequentes.", st))

    # --- 5.2 Flow Velocity ---------------------------------------------------
    story.append(H2("5.2  Flow Velocity / Throughput", st))
    story.append(P(
        "<b>O que e medido?</b> O throughput -- ou seja, quantos issues a equipa fecha "
        "por semana ou por PI. Uma velocidade consistentemente alta indica uma equipa "
        "com capacidade de entrega.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Grafico", "Mostra"],
        [
            ["Frequencia diaria (histograma)",
             "Com que frequencia sao fechados exatamente 1, 2, 3 ... issues num unico dia. "
             "Mostra a producao diaria tipica."],
            ["Tendencia semanal (grafico de linhas)",
             "Numero de issues fechados por semana ao longo de todo o periodo. "
             "As flutuacoes e tendencias ficam imediatamente visiveis."],
            ["Tendencia PI (grafico de barras)",
             "Numero de issues fechados por PI (Program Increment) ou trimestre. "
             "A linha vermelha mostra a media. Cores das barras: "
             "Cinzento = primeira barra; Laranja = PI atual; Azul = PIs concluidos; "
             "Cinzento claro = PIs futuros."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("velocity_daily",
            "Fig. 3: Frequencia diaria -- frequencia das contagens de fecho diario.")
    add_img("velocity_weekly",
            "Fig. 4: Tendencia semanal -- issues fechados por semana de calendario.")
    add_img("velocity_pi",
            "Fig. 5: Tendencia PI -- issues fechados por PI ou trimestre com linha de media.")

    # --- 5.3 Flow Load -------------------------------------------------------
    story.append(H2("5.3  Flow Load / WIP  (Work in Progress)", st))
    story.append(P(
        "<b>O que e medido?</b> Quantos issues estao simultaneamente em curso e "
        "qual a sua antiguidade. Demasiados issues em paralelo atrasam a entrega "
        "(quanto mais WIP, maior o tempo de ciclo).", st))
    story.append(SP(4))
    story.append(P(
        "O grafico mostra um box plot agrupado: cada etapa tem uma caixa que mostra "
        "a idade (em dias) dos issues atualmente nessa etapa. Os pontos individuais "
        "representam issues individuais -- no navegador ve a chave do issue ao passar "
        "o cursor.", st))
    story.append(SP(4))
    story.append(P(
        "As linhas de referencia tracejadas provenientes dos issues fechados (mediana, "
        "percentil 85, percentil 95) fornecem orientacao: issues ja acima do percentil 95 "
        "dos issues fechados estao significativamente atrasados.", st))
    add_img("flow_load",
            "Fig. 6: Flow Load -- idade dos issues em aberto por etapa com linhas de referencia dos issues fechados.")

    # --- 5.4 CFD -------------------------------------------------------------
    story.append(H2("5.4  Cumulative Flow Diagram (CFD)", st))
    story.append(P(
        "<b>O que e medido?</b> Quantos issues entraram no total em cada etapa -- "
        "acumulados ao longo do tempo, divididos por etapa do fluxo. Um sistema bem "
        "a funcionar mostra bandas paralelas a subir de forma uniforme, sem inchacos "
        "em etapas individuais.", st))
    story.append(SP(4))
    story.append(P(
        "O grafico e um diagrama de areas empilhadas: cada camada colorida corresponde "
        "a uma etapa. A primeira etapa esta no topo, a ultima (Done/Closed) na base. "
        "O grafico comeca sempre em 0 -- independentemente da data de inicio selecionada. "
        "Duas linhas de tendencia a preto mostram:", st))
    story.append(BL(
        "<b>Linha superior (entrada):</b> Corre ao longo da margem visual superior da "
        "etapa &lt;First&gt; (entrada no sistema). Sem ficheiro de fluxo: primeira etapa.", st))
    story.append(BL(
        "<b>Linha inferior (saida):</b> Corre ao longo da margem visual superior da "
        "etapa &lt;Closed&gt; (conclusao no sistema). Sem ficheiro de fluxo: ultima etapa.",
        st))
    add_img("cfd",
            "Fig. 7: Cumulative Flow Diagram -- entradas cumulativas por etapa com linhas de tendencia de entrada e saida.")
    story.append(SP(4))
    story.append(P(
        "O <b>racio In/Out</b> no titulo do grafico (por exemplo 'Ratio In/out 1.80 : 1') "
        "mostra se entra mais do que e concluido. Um valor de 1.0 significa um sistema "
        "equilibrado; valores significativamente acima de 1.0 indicam um backlog crescente.",
        st))
    story.append(SP(4))
    story.append(P(
        "O eixo x mostra limites mensais com etiquetas grandes (por exemplo 'Jan 2025') e "
        "semanas do calendario ISO com etiquetas cinzentas pequenas (por exemplo 'W03'), "
        "para que as etiquetas nao se sobreponham.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nota:</b> O CFD requer o ficheiro CFD.xlsx opcional. Sem este ficheiro "
        "a metrica CFD nao pode ser calculada.", st, "#fff8e1"))

    # --- 5.5 Flow Distribution -----------------------------------------------
    story.append(H2("5.5  Flow Distribution", st))
    story.append(P(
        "<b>O que e medido?</b> A composicao de todos os issues por tipo, etapa dominante "
        "e tempo de ciclo medio. Mostra de imediato que tipos de issue dominam, "
        "onde os issues passam mais tempo e quais os tipos processados mais rapida ou "
        "lentamente.", st))
    story.append(SP(4))
    story.append(P(
        "O grafico e composto por tres sub-graficos lado a lado:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Grafico", "O que e mostrado?"],
        [
            ["By Issue Type (donut)",
             "Contagem e percentagem dos issues por tipo de issue. Todos os issues sao incluidos."],
            ["Stage Prominence (donut)",
             "Para cada issue e identificada a etapa em que passou mais tempo. "
             "O grafico conta quantas vezes cada etapa foi dominante em todos os issues. "
             "Para issues fechados, a etapa terminal Done (estado atual) e excluida, "
             "para que o tempo de espera apos o fecho nao distorca o resultado. "
             "O subtitulo mostra o numero de issues contribuintes (n=...). "
             "Issues sem dados de etapa nao sao contados."],
            ["Avg Cycle Time by Type (barras)",
             "Tempo de ciclo medio em dias por tipo de issue (Metodo A: "
             "Closed Date - First Date). Apenas issues com ambos os campos de data e "
             "CT > 0 sao incluidos. Etiquetas das barras no formato '15.0d'."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_dist",
            "Fig. 8: Flow Distribution -- distribuicao por tipo de issue, Stage Prominence e tempo de ciclo medio por tipo.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretacao Stage Prominence:</b> Se uma etapa domina com particular "
        "frequencia, os issues ficam la desproporcionalmente tempo -- um possivel "
        "estrangulamento no fluxo. Os issues fechados sao incluidos, mas a sua etapa "
        "terminal Done e ocultada, para que os reais estrangulamentos de processamento "
        "permanecam visiveis.", st))

    # --- 5.6 Process Flow: Transitions ----------------------------------------
    story.append(H2("5.6  Process Flow: Transitions", st))
    story.append(P(
        "<b>O que e medido?</b> Todas as transicoes de estado dos issues sao visualizadas "
        "como um grafo dirigido: nos = estados, setas = transicoes. A espessura das setas "
        "e proporcional a frequencia da transicao. Isto torna imediatamente claro que "
        "caminhos os issues percorrem no fluxo, com que frequencia ocorre retrabalho e "
        "onde os issues ficam presos em ciclos.", st))
    story.append(SP(4))
    story.append(P(
        "Esta metrica requer o ficheiro opcional <b>Transitions.xlsx</b> (do "
        "transform_data). Sem este ficheiro aparece um aviso no registo.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Elemento", "Significado"],
        [
            ["Seta azul",    "Transicao para a frente -- o issue avanca no fluxo."],
            ["Seta vermelha","Transicao para tras (retrabalho) -- o issue regressa a uma etapa anterior."],
            ["Arco laranja", "Self-loop -- o issue permanece no mesmo estado (por exemplo, etapa percorrida novamente)."],
            ["Espessura da seta", "Quanto mais espessa a seta, mais frequente esta transicao."],
            ["Numero na seta",   "Contagem absoluta desta transicao em todos os issues."],
            ["No",           "Circulo azul escuro com nome de estado. Ordem: etapas do fluxo primeiro "
                             "(no sentido dos ponteiros do relogio), depois estados adicionais por ordem alfabetica."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow",
            "Fig. 9: Process Flow: Transitions -- grafo dirigido de todas as transicoes de estado com espessura e codificacao por cores.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretacao:</b> Muitas setas vermelhas significam retrabalho frequente -- "
        "um sinal de problemas de qualidade ou requisitos pouco claros. Setas azuis espessas "
        "mostram o caminho principal do fluxo. "
        "Os self-loops (laranja) ocorrem quando um issue e colocado no mesmo estado "
        "multiplas vezes.", st))

    # --- 5.7 Process Flow: Time -----------------------------------------------
    story.append(H2("5.7  Process Flow: Time", st))
    story.append(P(
        "<b>O que e medido?</b> O mesmo grafo dirigido que Process Flow: Transitions, "
        "mas com enfoque no <b>tempo</b>: a largura dos nos e as etiquetas das arestas "
        "baseiam-se na mediana do tempo de permanencia da etapa de origem. Isto torna "
        "imediatamente visivel em que etapas os issues esperam mais e que transicoes "
        "custam mais tempo.", st))
    story.append(SP(4))
    story.append(P(
        "Esta metrica tambem requer o ficheiro opcional <b>Transitions.xlsx</b> "
        "(do transform_data).", st))
    story.append(SP(4))
    story.append(tbl(
        ["Elemento", "Significado"],
        [
            ["Largura do no",       "Proporcional a mediana do tempo de permanencia nesta etapa."],
            ["Largura da aresta",   "Proporcional a mediana do tempo de permanencia da etapa de origem."],
            ["Numero na seta",      "Mediana do tempo de permanencia da etapa de origem em dias (d) para issues que tomaram exatamente esta transicao."],
            ["Seta azul",           "Transicao para a frente."],
            ["Seta vermelha",       "Transicao para tras (retrabalho)."],
            ["Arco laranja",        "Self-loop."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow_time",
            "Fig. 10: Process Flow: Time -- largura dos nos e etiquetas das arestas baseadas na mediana do tempo de permanencia por etapa.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretacao:</b> Nos largos e arestas espessas indicam etapas onde os issues "
        "permanecem particularmente tempo -- possiveis estrangulamentos. Comparando com "
        "Process Flow: Transitions, pode verificar-se se transicoes frequentes tambem "
        "implicam peso temporal significativo ou sao apenas breves mudancas de estado.", st))

    # =========================================================================
    # 6. Exportacao PDF
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("6  Exportacao PDF", st))
    story.append(P(
        "A exportacao PDF cria um ficheiro PDF de multiplas paginas com todos os graficos "
        "selecionados. Cada grafico aparece na sua propria pagina.", st))
    story.append(SP(6))
    story.append(tbl(
        ["Passo", "Acao"],
        [
            ["1", "Carregar ficheiros e definir filtros (conforme descrito no Capitulo 4)."],
            ["2", "Selecionar as metricas pretendidas atraves das caixas de selecao."],
            ["3", "Clicar em 'Exportar relatorios'."],
            ["4", "Na caixa de dialogo de guardar, escolher nome e local do ficheiro e confirmar."],
            ["5", "O programa calcula e exporta; o progresso aparece no registo."],
            ["6", "Apos a conclusao, o PDF e o Excel de relatorio estao disponiveis no local escolhido."],
        ],
        col_widths=[1.5*cm, 14.5*cm]))
    story.append(SP(8))
    story.append(H2("6.1  Excel de relatorio automatico", st))
    story.append(P(
        "Em cada exportacao PDF e criado automaticamente um ficheiro Excel com o mesmo "
        "nome (por exemplo report.xlsx junto a report.pdf). Este ficheiro contem todos "
        "os issues filtrados no formato IssueTimes, complementado por tres colunas:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Coluna", "Conteudo"],
        [
            ["Status Group",
             "Grupo de estado do issue: 'To Do' (ainda nao iniciado), "
             "'In Progress' (em processamento) ou 'Done' (concluido). "
             "Derivado de First Date e Closed Date."],
            ["Cycle Time (First->Closed)",
             "Tempo de ciclo em dias de calendario de First Date a Closed Date "
             "(Metodo A). Vazio se alguma das datas estiver em falta."],
            ["Cycle Time B (days in Status)",
             "Soma de minutos em todas as etapas do fluxo exceto a ultima, "
             "dividida por 1440 (Metodo B). Vazio se alguma das datas estiver em falta."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(SP(8))
    story.append(box(
        "<b>Issues zero-day:</b> Dois mecanismos funcionam de forma independente:<br/>"
        "1. <b>Filtro de exclusao (antes do calculo):</b> Se a caixa de selecao "
        "'Excluir issues zero-day' estiver ativa, os issues com um tempo de ciclo abaixo "
        "do limiar configurado (padrao: 5 minutos) sao completamente removidos de todas "
        "as metricas.<br/>"
        "2. <b>Dentro da metrica Flow Time:</b> Issues com um tempo de ciclo de 0 dias "
        "(mesmo dia de calendario) sao reportados separadamente e nao incluidos nas "
        "estatisticas.<br/>"
        "Em ambos os casos e criado um ficheiro Excel separado "
        "(por exemplo report_zero_day_issues.xlsx na mesma pasta).", st,
        "#fff8e1"))

    # =========================================================================
    # 7. FAQ
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("7  Perguntas Frequentes", st))

    faqs = [
        (
            "Os graficos nao aparecem no navegador.",
            "Verifique se esta configurado um navegador predefinido. Experimente "
            "alternativamente a exportacao PDF. Certifique-se de que o ficheiro "
            "IssueTimes foi carregado corretamente (consulte o registo)."
        ),
        (
            "A exportacao PDF demora muito ou falha.",
            "A renderizacao dos graficos como PDF requer o pacote Kaleido. Se este ainda "
            "nao foi configurado, contacte o seu responsavel tecnico."
        ),
        (
            "O registo mostra 'Stage only in IssueTimes' ou 'Stage only in CFD'.",
            "As colunas de etapa em IssueTimes.xlsx e CFD.xlsx nao correspondem. Isto e "
            "um aviso que nao interrompe a analise, mas indica que os ficheiros provem "
            "de versoes diferentes do fluxo."
        ),
        (
            "Como posso analisar apenas um projeto especifico?",
            "Introduza a chave do projeto pretendido no campo 'Projetos' (por exemplo ARTA). "
            "Separe varios projetos com virgula. Em alternativa: utilize o botao de selecao "
            "para uma lista de todos os projetos disponiveis."
        ),
        (
            "O Cumulative Flow Diagram nao aparece.",
            "A metrica CFD requer um ficheiro CFD.xlsx. Carregue-o no campo "
            "'CFD (opcional)'."
        ),
        (
            "O Process Flow mostra 'No transition data available'.",
            "A metrica Process Flow requer um ficheiro Transitions.xlsx do transform_data. "
            "Carregue-o no campo 'Transitions (opcional)'. Certifique-se de que o ficheiro "
            "provem da mesma execucao de exportacao que o IssueTimes.xlsx."
        ),
        (
            "Qual e a diferenca entre intervalos PI e trimestres?",
            "Por defeito, sao utilizados os trimestres do calendario (Q1-Q4) como "
            "intervalos de tempo. Com um ficheiro de configuracao PI pode definir os seus "
            "proprios intervalos que correspondam aos seus PIs reais -- por exemplo se o "
            "seu PI comeca a 6 de janeiro em vez de 1 de janeiro."
        ),
        (
            "Como guardo as minhas definicoes?",
            "Utilize o menu 'Templates' -> 'Guardar...' para guardar todas as definicoes "
            "atuais num ficheiro JSON. Da proxima vez: 'Templates' -> 'Carregar...'. As "
            "definicoes de exclusao podem ser adicionalmente guardadas de forma permanente "
            "em 'Templates' -> 'Guardar exclusoes como padrao'."
        ),
        (
            "Um issue aparece nas metricas embora nunca tenha sido realmente trabalhado.",
            "Isto acontece quando um issue foi clicado manualmente por todas as etapas "
            "do fluxo em segundos -- sem qualquer trabalho de desenvolvimento real. Ative "
            "a caixa de selecao 'Excluir issues zero-day' em 'Exclusoes' na GUI "
            "(limiar por exemplo 5 minutos). O issue e entao completamente removido de "
            "todas as metricas e documentado num ficheiro Excel separado."
        ),
        (
            "Posso apresentar os resultados sem um computador?",
            "Sim: exporte primeiro um relatorio PDF. O ficheiro PDF contem todos os "
            "graficos e pode ser aberto em qualquer dispositivo. Para apresentacoes "
            "interativas, recomenda-se a visualizacao no navegador."
        ),
    ]
    for q, a in faqs:
        story.append(H3("P: " + q, st))
        story.append(P("R: " + a, st))
        story.append(SP(4))

    # =========================================================================
    # 8. Glossario
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("8  Glossario", st))
    story.append(tbl(
        ["Termo", "Explicacao"],
        [
            ["Closed Date",    "A data em que um issue foi concluido."],
            ["Cycle Time",     "Designacao alternativa para Flow Time (terminologia Global)."],
            ["First Date",     "Data do primeiro trabalho ativo num issue."],
            ["Flow Load",      "Numero de issues atualmente em curso (termo SAFe)."],
            ["Flow Time",      "Tempo de ciclo desde o primeiro trabalho ate a conclusao."],
            ["Flow Velocity",  "Numero de issues concluidos por periodo de tempo (termo SAFe)."],
            ["Issue",          "Um ticket no sistema de tickets (por exemplo, um cartao Jira)."],
            ["Issue type",     "Categoria de um issue, por exemplo Feature, Bug, Story, Task."],
            ["IssueTimes",     "O ficheiro Excel com todos os issues produzido pelo transform_data."],
            ["JSON",           "Formato de texto simples para ficheiros de configuracao."],
            ["LOESS",          "Metodo de suavizacao estatistica para linhas de tendencia."],
            ["P85 / P95",      "Percentil 85 / 95 dos tempos de ciclo."],
            ["PI",             "Program Increment -- um periodo fixo de planeamento e entrega."],
            ["Process Flow: Transitions", "Grafo dirigido de todas as transicoes de estado (baseado em frequencia). Mostra caminhos principais, retrabalhos e ciclos no fluxo."],
            ["Process Flow: Time",        "Grafo dirigido de todas as transicoes de estado (baseado em tempo). A largura dos nos e as etiquetas das arestas mostram a mediana do tempo de permanencia por etapa."],
            ["Resolution",     "Tipo de resolucao de um issue, por exemplo 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework -- uma framework para escalamento agil."],
            ["Stage",          "Um passo no fluxo, por exemplo Analysis, Implementation, Done."],
            ["Template",       "Ficheiro de configuracao guardado com todas as definicoes."],
            ["Throughput",     "Designacao alternativa para Flow Velocity (terminologia Global)."],
            ["Transitions",    "Registo de cada mudanca de estado por issue. Exportado pelo transform_data como Transitions.xlsx."],
            ["WIP",            "Work in Progress -- issues que estao atualmente a ser trabalhados."],
            ["Zero-day issue", "Um issue cujo tempo de ciclo (First to Closed Date) e tao curto "
                               "que nao representa tempo de processamento real. Normalmente causado "
                               "por clicar manualmente pelo fluxo. Pode ser removido de todas as "
                               "metricas atraves de um filtro de limiar."],
        ],
        col_widths=[4*cm, 12*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content – French
# ---------------------------------------------------------------------------

def content_fr(st, images=None):
    """
    Build the full French document story with optional embedded chart images.

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
    story.append(H1("Table des matieres", st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOCH1fr", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2fr", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3fr", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    story.append(toc)

    # =========================================================================
    # 1. Introduction
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("1  Qu'est-ce que build_reports ?", st))
    story.append(P(
        "build_reports est un outil qui cree automatiquement des diagrammes pertinents sur "
        "la progression et l'efficacite de votre equipe agile. En entree, il utilise les "
        "donnees que le module <b>transform_data</b> a exportees depuis votre gestionnaire "
        "de tickets (par ex. Jira). build_reports lit ces fichiers et calcule plusieurs "
        "<b>metriques de flux</b> -- des analyses graphiques montrant a quelle vitesse et "
        "en quelle quantite votre equipe livre.", st))
    story.append(P(
        "Le programme dispose d'une interface graphique simple (GUI) : aucune connaissance "
        "en programmation n'est requise. En un clic, les diagrammes s'affichent dans le "
        "navigateur ou sont enregistres sous forme de fichier PDF.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Apercu des metriques</b><br/>"
        "- <b>Flow Time / Cycle Time</b> : Combien de temps faut-il pour qu'un ticket soit termine ?<br/>"
        "- <b>Flow Velocity / Throughput</b> : Combien de tickets l'equipe cloture-t-elle par semaine ?<br/>"
        "- <b>Flow Load / WIP</b> : Combien de tickets sont en cours simultanement ?<br/>"
        "- <b>Cumulative Flow Diagram</b> : Comment l'inventaire evolue-t-il dans le temps ?<br/>"
        "- <b>Flow Distribution</b> : Comment les tickets se repartissent-ils par type, etape et duree ?<br/>"
        "- <b>Process Flow: Transitions</b> : Quels chemins les tickets empruntent-ils ? Ou se produisent les retours et les boucles ?<br/>"
        "- <b>Process Flow: Time</b> : Combien de temps les tickets sejournent-ils dans chaque etape ? Quelles transitions coutent le plus de temps ?", st))

    # =========================================================================
    # 2. Prerequis et installation
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Prerequis et installation", st))

    story.append(H2("2.1  Que faut-il installer ?", st))
    story.append(P(
        "build_reports est fourni sous forme de <b>package portable</b>. Aucune "
        "installation Python separee n'est necessaire.", st))
    story.append(BL(
        "<b>Windows :</b> Python 3.11 est deja inclus dans le package -- il suffit de "
        "decompresser et d'executer.", st))
    story.append(BL(
        "<b>macOS / Linux :</b> Au premier lancement, un environnement Python est configure "
        "automatiquement (environ 1 minute, connexion Internet requise). Ensuite "
        "l'application fonctionne hors ligne.", st))

    story.append(H2("2.2  Demarrer le programme", st))
    story.append(P(
        "Double-cliquez sur le lanceur approprie dans le dossier extrait :", st))
    story.append(BL(
        "<b>Windows :</b> Double-cliquez sur <b>BuildReports.bat</b> -- lance l'interface "
        "graphique sans fenetre de console.", st))
    story.append(BL(
        "<b>macOS :</b> Clic droit sur <b>BuildReports.command</b> -> <i>Ouvrir</i> "
        "(une fois, pour contourner Gatekeeper).", st))
    story.append(BL(
        "<b>Linux :</b> Dans un terminal : "
        "<font name='Courier'>./BuildReports.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Conseil (Windows) :</b> Au premier lancement, SmartScreen peut afficher un "
        "avertissement. Cliquez sur <b>Informations complementaires</b> -> "
        "<b>Executer quand meme</b>.", st, "#e8f8f0"))

    # =========================================================================
    # 3. Fichiers d'entree
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("3  Fichiers d'entree", st))
    story.append(P(
        "build_reports requiert un ou deux fichiers Excel produits par le module "
        "<b>transform_data</b>. Ces fichiers ne doivent pas etre modifies manuellement -- "
        "la structure doit correspondre exactement au format attendu.", st))

    story.append(H2("3.1  IssueTimes.xlsx  (obligatoire)", st))
    story.append(P(
        "Ce fichier contient tous les tickets avec leurs donnees temporelles et leur "
        "statut de traitement actuel. Il est obligatoire pour toutes les metriques sauf "
        "le Cumulative Flow Diagram.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Colonne", "Signification"],
        [
            ["Project",       "Cle de projet (ex. ARTA)"],
            ["Key",           "Cle du ticket (ex. ARTA-123)"],
            ["Issuetype",     "Type de ticket (ex. Feature, Bug, Story)"],
            ["Status",        "Statut actuel (ex. In Progress, Done)"],
            ["Created",       "Date de creation du ticket"],
            ["First Date",    "Date a laquelle le ticket a ete activement traite pour la premiere fois"],
            ["Closed Date",   "Date de cloture (vide = encore ouvert)"],
            ["Resolution",    "Type de resolution (ex. Fixed, Duplicate)"],
            ["Stage columns", "Une colonne par etape du workflow avec les minutes passees dans cette etape"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.2  CFD.xlsx  (optionnel, pour le Cumulative Flow Diagram)", st))
    story.append(P(
        "Ce fichier contient les comptages journaliers d'entrees : combien de tickets ont "
        "<b>entre</b> dans une etape donnee chaque jour (pas des instantanes). "
        "build_reports accumule ces valeurs en un total cumulatif. Il n'est necessaire "
        "que si le Cumulative Flow Diagram doit etre calcule.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Colonne", "Signification"],
        [
            ["Day",           "Date (YYYY-MM-DD)"],
            ["Stage columns", "Une colonne par etape avec le nombre de nouvelles entrees ce jour-la"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.3  Fichier de configuration PI  (optionnel, pour Flow Velocity)", st))
    story.append(P(
        "Avec un fichier de configuration JSON optionnel, vous pouvez definir vos propres "
        "intervalles PI (Program Increments) pour le diagramme a barres Flow Velocity. "
        "Sans ce fichier, les trimestres calendaires sont utilises automatiquement.", st))
    story.append(SP(4))
    story.append(P("<b>Exemple (mode date) :</b>", st))
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
        "Le fichier doit avoir une extension <b>.json</b>. Copiez le fichier d'exemple "
        "fourni <b>pi_config_example.json</b> et ajustez les dates et les noms pour "
        "correspondre a votre calendrier PI. Le format doit etre conserve.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Remarque :</b> Utilisez toujours le format de date <b>YYYY-MM-DD</b> "
        "(annee-mois-jour). Exemple : 6 janvier 2025 = 2025-01-06.", st, "#fff8e1"))

    story.append(SP(8))
    story.append(H2("3.4  Transitions.xlsx  (optionnel, pour Process Flow)", st))
    story.append(P(
        "Ce fichier contient toutes les transitions de statut par ticket dans l'ordre "
        "chronologique. Il est produit par le module <b>transform_data</b> et est requis "
        "exclusivement pour la <b>metrique Process Flow</b>. Toutes les autres metriques "
        "peuvent etre calculees sans ce fichier.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Colonne", "Signification"],
        [
            ["Key",        "Cle du ticket (ex. ARTA-123)"],
            ["Transition", "Statut cible apres la transition (ex. 'In Analysis')"],
            ["Timestamp",  "Horodatage de la transition (DD.MM.YYYY HH:MM:SS)"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(SP(4))
    story.append(box(
        "<b>Remarque :</b> Transitions.xlsx et IssueTimes.xlsx doivent provenir du meme "
        "export transform_data afin que les cles de tickets correspondent.", st, "#fff8e1"))

    # =========================================================================
    # 4. Interface graphique
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("4  L'interface graphique (GUI)", st))
    story.append(P(
        "Apres le lancement, la fenetre principale s'ouvre. Elle se compose de trois "
        "zones : la <b>zone de fichiers</b> (haut), la <b>zone de filtres</b> (milieu) "
        "et la <b>zone d'actions</b> (bas) avec la fenetre de journal.", st))

    story.append(H2("4.1  Charger les fichiers", st))
    story.append(P("Chargez d'abord les fichiers necessaires :", st))
    story.append(BL(
        "<b>IssueTimes</b> -- Cliquez sur le bouton de dossier a droite du champ et "
        "selectionnez le fichier <b>IssueTimes.xlsx</b>. Apres le chargement, les projets "
        "disponibles et les types de tickets apparaissent automatiquement dans le journal.", st))
    story.append(BL(
        "<b>CFD (optionnel)</b> -- Selectionnez le fichier <b>CFD.xlsx</b> si vous avez "
        "besoin du Cumulative Flow Diagram.", st))
    story.append(BL(
        "<b>Workflow (optionnel)</b> -- Selectionnez le fichier texte de workflow de "
        "transform_data. Il contient les marqueurs <b>&lt;First&gt;</b> et "
        "<b>&lt;Closed&gt;</b> qui determinent quelles limites d'etapes les lignes de "
        "tendance du CFD marquent.", st))
    story.append(BL(
        "<b>Config PI (optionnel)</b> -- Selectionnez votre fichier de configuration JSON "
        "pour des intervalles PI personnalises. Laissez le champ vide pour utiliser les "
        "trimestres calendaires.", st))
    story.append(BL(
        "<b>Transitions (optionnel)</b> -- Selectionnez le fichier <b>Transitions.xlsx</b> "
        "de transform_data. Requis uniquement si la metrique Process Flow doit etre "
        "calculee.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Conseil :</b> Survoler un champ de saisie affiche une info-bulle expliquant "
        "a quoi sert ce champ.", st, "#e8f8f0"))

    story.append(H2("4.2  Parametrer les filtres", st))
    story.append(P(
        "Les filtres restreignent les tickets inclus dans l'analyse :", st))
    story.append(SP(4))
    story.append(tbl(
        ["Filtre / Exclusion", "Description"],
        [
            ["De / A",
             "Ne prendre en compte que les tickets clos dans cette plage de dates. "
             "Format : YYYY-MM-DD. Le bouton calendrier ouvre un selecteur de date."],
            ["365 derniers jours",
             "Definit automatiquement De et A sur les 365 derniers jours jusqu'a aujourd'hui."],
            ["Projets",
             "Analyser uniquement des projets specifiques. Separez plusieurs projets par une "
             "virgule, ex. ARTA, ARTB. Le bouton de selection affiche tous les projets disponibles."],
            ["Types de tickets",
             "Analyser uniquement des types de tickets specifiques, ex. Feature, Bug. "
             "Laisser vide = tous les types. Le bouton de selection affiche une liste de choix."],
            ["Exclure : Statut",
             "Supprimer completement les tickets ayant certains statuts Jira de toutes les "
             "metriques, ex. 'Canceled'. Le bouton de selection affiche tous les statuts existants."],
            ["Exclure : Resolution",
             "Exclure les tickets ayant certains types de resolution, ex. 'Won't Do' ou "
             "'Duplicate'. Le bouton de selection affiche toutes les resolutions existantes."],
            ["Exclure les tickets zero-day",
             "Case a cocher : les tickets dont le cycle time (First to Closed Date) est "
             "inferieur au seuil configure sont supprimes completement. Defaut : 5 minutes. "
             "Typique pour les tickets passes manuellement en revue dans le workflow sans "
             "aucun travail de developpement reel."],
        ],
        col_widths=[3.8*cm, 12.2*cm]))

    story.append(H2("4.3  Selectionner les metriques et la methode CT", st))
    story.append(P(
        "Utilisez les cases a cocher pour selectionner les metriques a calculer. "
        "Les boutons <b>Tout</b> et <b>Aucun</b> cochent ou decochen toutes les cases "
        "en meme temps.", st))
    story.append(SP(4))
    story.append(P(
        "La <b>methode CT</b> determine comment le cycle time est calcule -- pertinent "
        "uniquement pour la metrique Flow Time :", st))
    story.append(SP(4))
    story.append(tbl(
        ["Methode", "Calcul"],
        [
            ["Methode A (defaut)",
             "Difference en jours calendaires entre First Date et Closed Date. "
             "Simple et directe."],
            ["Methode B",
             "Somme des minutes dans les etapes individuelles du workflow (derniere etape "
             "exclue), divisee par 1440. Mesure uniquement le temps de traitement actif."],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(H2("4.4  Creer un rapport", st))
    story.append(P("Vous avez deux options :", st))
    story.append(BL(
        "<b>Afficher dans le navigateur</b> -- Tous les diagrammes sont ouverts dans votre "
        "navigateur par defaut. Les diagrammes y sont entierement interactifs : zoom, "
        "inspection des points de donnees via info-bulle au survol, et activation/desactivation "
        "de categories individuelles dans la legende.", st))
    story.append(BL(
        "<b>Exporter les rapports</b> -- Tous les diagrammes sont exportes dans un fichier "
        "PDF multi-pages. Une boite de dialogue d'enregistrement demande le nom et "
        "l'emplacement du fichier. En plus du PDF, deux fichiers Excel sont "
        "automatiquement crees : un Excel de rapport avec tous les tickets, groupes de "
        "statut et cycle times, et -- si des tickets zero-day existent -- un fichier "
        "separe pour ces tickets.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Remarque :</b> Pendant les calculs, l'interface est brievement bloquee. "
        "La progression est affichee dans la fenetre de journal. Ne fermez pas et ne "
        "cliquez pas jusqu'a ce que le journal affiche le message de fin.", st, "#fff8e1"))

    story.append(H2("4.5  Modeles -- enregistrer et charger une configuration", st))
    story.append(P(
        "Dans le menu <b>Modeles</b>, vous pouvez enregistrer tous les parametres actuels "
        "(chemins de fichiers, filtres, selection de metriques, methode CT, terminologie) "
        "sous forme de fichier JSON et les recharger ulterieuremen -- plus besoin de "
        "remplir tous les champs a chaque fois.", st))
    story.append(BL(
        "<b>Enregistrer...</b> -- Choisissez un emplacement et un nom pour le fichier de "
        "configuration (ex. monEquipe_RapportTrimestriel.json).", st))
    story.append(BL(
        "<b>Charger...</b> -- Ouvrez un fichier de configuration enregistre. Tous les "
        "champs sont remplis automatiquement. Si un fichier enregistre est introuvable, "
        "une note apparait dans le journal.", st))

    story.append(H2("4.6  Langue et terminologie", st))
    story.append(P(
        "La langue peut etre changee de deux facons :", st))
    story.append(BL(
        "<b>Bouton drapeau</b> dans le coin superieur droit de la fenetre -- affiche la "
        "langue actuelle sous forme de drapeau national. Un clic bascule instantanement "
        "entre l'allemand et l'anglais.", st))
    story.append(BL(
        "<b>Options -> Langue</b> -- alternativement via le menu.", st))
    story.append(P(
        "Via <b>Options -> Terminologie</b>, vous pouvez egalement basculer entre "
        "<b>SAFe</b> et <b>Global</b>. En mode SAFe, les metriques s'appellent par ex. "
        "'Flow Time', en mode Global 'Cycle Time'. Ce changement affecte uniquement les "
        "etiquettes, pas les calculs.", st))

    # =========================================================================
    # 5. Metriques
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("5  Apercu des metriques", st))
    story.append(P(
        "Cette section explique chaque metrique en termes simples : ce qu'elle mesure, "
        "ce que les diagrammes montrent et comment interpreter les resultats. "
        "Les diagrammes d'exemple sont bases sur un jeu de donnees exemple.", st))

    # --- 5.1 Flow Time -------------------------------------------------------
    story.append(H2("5.1  Flow Time / Cycle Time", st))
    story.append(P(
        "<b>Qu'est-ce qui est mesure ?</b> Le cycle time -- c'est-a-dire le nombre de "
        "jours qu'un ticket prend depuis le premier travail jusqu'a la completion. "
        "Moins c'est mieux.", st))

    story.append(H3("Diagramme 1 : Boite a moustaches (distribution)", st))
    story.append(P(
        "La boite a moustaches montre en un coup d'oeil comment les cycle times sont "
        "distribues. L'en-tete du diagramme contient les statistiques cles :", st))
    story.append(SP(4))
    story.append(tbl(
        ["Statistique", "Signification"],
        [
            ["Min / Max",   "Cycle time le plus court et le plus long mesure"],
            ["Q1 / Q3",     "25 % / 75 % des tickets sont en dessous de cette valeur"],
            ["Mediane",     "Le cycle time median -- 50 % des tickets sont en dessous"],
            ["Moyenne",     "Cycle time moyen (peut etre fausse par les valeurs aberrantes)"],
            ["90d CT%",     "Part des tickets avec cycle time <= 90 jours (Service Level Expectation)"],
            ["P85 / P95",   "85 % / 95 % des tickets ont ete termines dans ce delai"],
            ["Ecart-type",  "Ecart-type -- dans quelle mesure les valeurs varient-elles ?"],
            ["CV",          "Coefficient de variation -- dispersion relative (plus petit = processus plus stable)"],
            ["Zero-Day",    "Nombre de tickets avec cycle time 0 (exclus de l'analyse)"],
        ],
        col_widths=[3*cm, 13*cm]))
    story.append(SP(4))
    story.append(HI(
        "Point rouge dans la boite a moustaches = valeur aberrante statistique. Dans le "
        "navigateur, vous pouvez lire la cle du ticket via l'info-bulle au survol.", st))
    add_img("flow_time_box",
            "Fig. 1 : Boite a moustaches des cycle times -- distribution, quartiles et en-tete de statistiques.")

    story.append(H3("Diagramme 2 : Nuage de points (tendance dans le temps)", st))
    story.append(P(
        "Chaque point est un ticket termine. L'axe x montre la date de cloture, "
        "l'axe y le cycle time en jours. Les couleurs et les lignes de reference "
        "facilitent l'interpretation :", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Signification"],
        [
            ["Point bleu",    "Tickets normaux (en dessous du 85e percentile)"],
            ["Point orange",  "Tickets lents (entre le 85e et le 95e percentile)"],
            ["Point rouge",   "Tickets tres lents (au-dessus du 95e percentile)"],
            ["Courbe bleue",  "Ligne de tendance LOESS -- montre la tendance du cycle time dans le temps"],
            ["Ligne rouge",   "Ligne de reference mediane"],
            ["Ligne verte",   "Ligne de reference du 85e percentile"],
            ["Ligne cyan",    "Ligne de reference du 95e percentile"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_time_scatter",
            "Fig. 2 : Nuage de points -- cycle time par date de cloture avec ligne de tendance LOESS et lignes de reference.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation :</b> Si la ligne de tendance LOESS monte vers la droite, les "
        "tickets ralentissent au fil du temps. Une ligne plate signale un processus stable. "
        "De nombreux points rouges et oranges indiquent des goulets d'etranglement frequents.", st))

    # --- 5.2 Flow Velocity ---------------------------------------------------
    story.append(H2("5.2  Flow Velocity / Throughput", st))
    story.append(P(
        "<b>Qu'est-ce qui est mesure ?</b> Le debit -- c'est-a-dire combien de tickets "
        "l'equipe cloture par semaine ou par PI. Une velocity constamment elevee indique "
        "une equipe capable de livrer.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Diagramme", "Montre"],
        [
            ["Frequence journaliere (histogramme)",
             "A quelle frequence exactement 1, 2, 3 ... tickets sont clos en une seule "
             "journee. Montre la production journaliere typique."],
            ["Tendance hebdomadaire (graphique lineaire)",
             "Nombre de tickets clos par semaine sur toute la periode. "
             "Les fluctuations et les tendances deviennent immediatement visibles."],
            ["Tendance PI (diagramme a barres)",
             "Nombre de tickets clos par PI (Program Increment) ou trimestre. "
             "La ligne rouge montre la moyenne. Couleurs des barres : "
             "Gris = premiere barre ; Orange = PI en cours ; Bleu = PIs termines ; "
             "Gris clair = PIs futurs."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("velocity_daily",
            "Fig. 3 : Frequence journaliere -- frequence des nombres de clotures journalieres.")
    add_img("velocity_weekly",
            "Fig. 4 : Tendance hebdomadaire -- tickets clos par semaine calendaire.")
    add_img("velocity_pi",
            "Fig. 5 : Tendance PI -- tickets clos par PI ou trimestre avec ligne moyenne.")

    # --- 5.3 Flow Load -------------------------------------------------------
    story.append(H2("5.3  Flow Load / WIP  (Work in Progress)", st))
    story.append(P(
        "<b>Qu'est-ce qui est mesure ?</b> Combien de tickets sont simultanement en cours "
        "et depuis combien de temps. Trop de tickets en parallele ralentit la livraison "
        "(plus le WIP est eleve, plus le cycle time est long).", st))
    story.append(SP(4))
    story.append(P(
        "Le diagramme montre une boite a moustaches groupee : chaque etape obtient une "
        "boite montrant l'age (en jours) des tickets qui s'y trouvent actuellement. "
        "Les points individuels representent des tickets individuels -- dans le navigateur, "
        "vous voyez la cle du ticket au survol.", st))
    story.append(SP(4))
    story.append(P(
        "Des lignes de reference en pointilles issues des tickets termines (mediane, "
        "85e percentile, 95e percentile) donnent des reperes : les tickets deja au-dessus "
        "du 95e percentile des tickets termines accusent un retard significatif.", st))
    add_img("flow_load",
            "Fig. 6 : Flow Load -- age des tickets ouverts par etape avec lignes de reference issues des tickets termines.")

    # --- 5.4 CFD -------------------------------------------------------------
    story.append(H2("5.4  Cumulative Flow Diagram (CFD)", st))
    story.append(P(
        "<b>Qu'est-ce qui est mesure ?</b> Combien de tickets au total ont entre dans "
        "chaque etape -- cumules dans le temps, par etape de workflow. Un systeme bien "
        "fonctionnel montre des bandes paralleles montant regulierement sans gonflement "
        "dans des etapes individuelles.", st))
    story.append(SP(4))
    story.append(P(
        "Le diagramme est un graphique de surface empilee : chaque couche coloree "
        "correspond a une etape. La premiere etape est en haut, la derniere "
        "(Done/Closed) en bas. Le diagramme commence toujours a 0 -- quelle que soit "
        "la date de debut selectionnee. Deux lignes de tendance noires montrent :", st))
    story.append(BL(
        "<b>Ligne superieure (entrees) :</b> Suit le bord superieur visuel de l'etape "
        "&lt;First&gt; (entree dans le systeme). Sans fichier workflow : premiere etape.", st))
    story.append(BL(
        "<b>Ligne inferieure (sorties) :</b> Suit le bord superieur visuel de l'etape "
        "&lt;Closed&gt; (completion dans le systeme). Sans fichier workflow : derniere etape.", st))
    add_img("cfd",
            "Fig. 7 : Cumulative Flow Diagram -- entrees cumulatives par etape avec lignes de tendance entrees et sorties.")
    story.append(SP(4))
    story.append(P(
        "Le <b>ratio In/Out</b> dans le titre du diagramme (ex. 'Ratio In/out 1.80 : 1') "
        "indique si davantage entre que ce qui est termine. Une valeur de 1.0 signifie un "
        "systeme equilibre ; des valeurs nettement superieures a 1.0 indiquent un backlog "
        "croissant.", st))
    story.append(SP(4))
    story.append(P(
        "L'axe x montre les limites de mois avec de grandes etiquettes (ex. 'Jan 2025') "
        "et les semaines ISO avec de petites etiquettes grises (ex. 'W03'), afin que les "
        "etiquettes ne se chevauchent pas.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Remarque :</b> Le CFD requiert le fichier optionnel CFD.xlsx. Sans ce fichier, "
        "la metrique CFD ne peut pas etre calculee.", st, "#fff8e1"))

    # --- 5.5 Flow Distribution -----------------------------------------------
    story.append(H2("5.5  Flow Distribution", st))
    story.append(P(
        "<b>Qu'est-ce qui est mesure ?</b> La composition de tous les tickets par type, "
        "etape dominante et cycle time moyen. Montre en un coup d'oeil quels types de "
        "tickets dominent, ou les tickets passent le plus de temps, et quels types sont "
        "traites le plus rapidement ou le plus lentement.", st))
    story.append(SP(4))
    story.append(P(
        "Le diagramme se compose de trois sous-diagrammes cote a cote :", st))
    story.append(SP(4))
    story.append(tbl(
        ["Diagramme", "Ce qui est montre"],
        [
            ["Par type de ticket (anneau)",
             "Nombre et part en pourcentage des tickets par type de ticket. Tous les tickets sont inclus."],
            ["Stage Prominence (anneau)",
             "Pour chaque ticket, l'etape dans laquelle il a passe le plus de temps est identifiee. "
             "Le diagramme compte combien de fois chaque etape a ete dominante sur tous les tickets. "
             "Pour les tickets termines, l'etape terminale Done (statut actuel) est exclue, "
             "afin que le temps d'attente apres la cloture ne fausse pas le resultat. "
             "Le sous-titre indique le nombre de tickets contribuant (n=...). "
             "Les tickets sans donnees d'etape ne sont pas comptes."],
            ["Cycle time moyen par type (barres)",
             "Cycle time moyen en jours par type de ticket (Methode A : "
             "Closed Date - First Date). Seuls les tickets avec les deux champs de date et "
             "CT > 0 sont inclus. Etiquettes de barres au format '15.0j'."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    add_img("flow_dist",
            "Fig. 8 : Flow Distribution -- distribution par type de ticket, Stage Prominence et cycle time moyen par type.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation Stage Prominence :</b> Si une etape domine particulierement "
        "souvent, les tickets y sejournent de maniere disproportionnee -- un goulet "
        "d'etranglement potentiel dans le workflow. Les tickets termines sont inclus, "
        "mais leur etape terminale Done est masquee, de sorte que les vrais goulets "
        "d'etranglement de traitement restent visibles.", st))

    # --- 5.6 Process Flow: Transitions ----------------------------------------
    story.append(H2("5.6  Process Flow: Transitions", st))
    story.append(P(
        "<b>Qu'est-ce qui est mesure ?</b> Toutes les transitions de statut des tickets "
        "sont visualisees sous forme de graphe oriente : noeuds = statuts, fleches = "
        "transitions. L'epaisseur des fleches est proportionnelle a la frequence de la "
        "transition. Cela rend immediatement visible quels chemins les tickets empruntent "
        "dans le workflow, a quelle frequence des retours se produisent et ou les tickets "
        "restent bloques dans des boucles.", st))
    story.append(SP(4))
    story.append(P(
        "Cette metrique requiert le fichier optionnel <b>Transitions.xlsx</b> (de "
        "transform_data). Sans ce fichier, un avertissement apparait dans le journal.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Signification"],
        [
            ["Fleche bleue",    "Transition en avant -- le ticket avance dans le workflow."],
            ["Fleche rouge",    "Transition en arriere (retour) -- le ticket revient a une etape anterieure."],
            ["Arc orange",      "Auto-boucle -- le ticket reste dans le meme statut (ex. etape traversee a nouveau)."],
            ["Largeur de fleche", "Plus la fleche est epaisse, plus cette transition est frequente."],
            ["Chiffre sur la fleche", "Nombre absolu de cette transition sur tous les tickets."],
            ["Noeud",           "Cercle bleu fonce avec le nom du statut. Ordre : etapes du workflow d'abord "
                                "(sens horaire), puis statuts supplementaires par ordre alphabetique."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow",
            "Fig. 9 : Process Flow: Transitions -- graphe oriente de toutes les transitions de statut avec largeur d'arete et codage couleur.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation :</b> De nombreuses fleches rouges signifient de frequents "
        "retours -- signe de problemes de qualite ou d'exigences peu claires. Les "
        "fleches bleues epaisses montrent le chemin principal du workflow. Les "
        "auto-boucles (orange) se produisent lorsqu'un ticket est mis plusieurs fois "
        "dans le meme statut.", st))

    # --- 5.7 Process Flow: Time -----------------------------------------------
    story.append(H2("5.7  Process Flow: Time", st))
    story.append(P(
        "<b>Qu'est-ce qui est mesure ?</b> Le meme graphe oriente que Process Flow: "
        "Transitions, mais avec un focus sur le <b>temps</b> : la largeur des noeuds et "
        "les etiquettes des aretes sont basees sur le temps de sejour median de l'etape "
        "source. Cela rend immediatement visible dans quelles etapes les tickets attendent "
        "le plus longtemps et quelles transitions coutent le plus de temps.", st))
    story.append(SP(4))
    story.append(P(
        "Cette metrique requiert egalement le fichier optionnel <b>Transitions.xlsx</b> "
        "(de transform_data).", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Signification"],
        [
            ["Largeur du noeud",      "Proportionnelle au temps de sejour median dans cette etape."],
            ["Largeur de l'arete",    "Proportionnelle au temps de sejour median de l'etape source."],
            ["Chiffre sur la fleche", "Temps de sejour median de l'etape source en jours (j) pour les tickets ayant emprunte exactement cette transition."],
            ["Fleche bleue",          "Transition en avant."],
            ["Fleche rouge",          "Transition en arriere (retour)."],
            ["Arc orange",            "Auto-boucle."],
        ],
        col_widths=[4*cm, 12*cm]))
    add_img("process_flow_time",
            "Fig. 10 : Process Flow: Time -- largeur des noeuds et etiquettes d'aretes basees sur le temps de sejour median par etape.")
    story.append(SP(4))
    story.append(box(
        "<b>Interpretation :</b> Les noeuds larges et les aretes epaisses indiquent des "
        "etapes ou les tickets sejournent particulierement longtemps -- des goulets "
        "d'etranglement potentiels. Compare a Process Flow: Transitions, vous pouvez "
        "voir si des transitions frequentes comportent egalement un poids temporel "
        "significatif ou s'il s'agit simplement de brefs changements de statut.", st))

    # =========================================================================
    # 6. Export PDF
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("6  Export PDF", st))
    story.append(P(
        "L'export PDF cree un fichier PDF multi-pages avec tous les diagrammes "
        "selectionnes. Chaque diagramme apparait sur sa propre page.", st))
    story.append(SP(6))
    story.append(tbl(
        ["Etape", "Action"],
        [
            ["1", "Charger les fichiers et definir les filtres (comme decrit au chapitre 4)."],
            ["2", "Selectionner les metriques souhaitees via les cases a cocher."],
            ["3", "Cliquer sur 'Exporter les rapports'."],
            ["4", "Dans la boite de dialogue, choisir un nom de fichier et un emplacement et confirmer."],
            ["5", "Le programme calcule et exporte ; la progression apparait dans le journal."],
            ["6", "Apres completion, le PDF et l'Excel de rapport sont disponibles a l'emplacement choisi."],
        ],
        col_widths=[1.5*cm, 14.5*cm]))
    story.append(SP(8))
    story.append(H2("6.1  Excel de rapport automatique", st))
    story.append(P(
        "A chaque export PDF, un fichier Excel portant le meme nom est automatiquement "
        "cree (ex. report.xlsx a cote de report.pdf). Ce fichier contient tous les "
        "tickets filtres au format IssueTimes, complete par trois colonnes :", st))
    story.append(SP(4))
    story.append(tbl(
        ["Colonne", "Contenu"],
        [
            ["Status Group",
             "Groupe de statut du ticket : 'To Do' (pas encore commence), "
             "'In Progress' (en cours de traitement) ou 'Done' (termine). "
             "Derive de First Date et Closed Date."],
            ["Cycle Time (First->Closed)",
             "Cycle time en jours calendaires de First Date a Closed Date "
             "(Methode A). Vide si l'une des dates est manquante."],
            ["Cycle Time B (days in Status)",
             "Somme des minutes dans toutes les etapes du workflow sauf la derniere, "
             "divisee par 1440 (Methode B). Vide si l'une des dates est manquante."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(SP(8))
    story.append(box(
        "<b>Tickets zero-day :</b> Deux mecanismes fonctionnent independamment :<br/>"
        "1. <b>Filtre d'exclusion (avant le calcul) :</b> Si la case "
        "'Exclure les tickets zero-day' est active, les tickets avec un cycle time "
        "inferieur au seuil configure (defaut : 5 minutes) sont completement supprimes "
        "de toutes les metriques.<br/>"
        "2. <b>Au sein de la metrique Flow Time :</b> Les tickets avec un cycle time de "
        "0 jour (meme jour calendaire) sont signales separement et non inclus dans les "
        "statistiques.<br/>"
        "Dans les deux cas, un fichier Excel separe est cree "
        "(ex. report_zero_day_issues.xlsx dans le meme dossier).", st,
        "#fff8e1"))

    # =========================================================================
    # 7. FAQ
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("7  Questions frequemment posees", st))

    faqs = [
        (
            "Les diagrammes n'apparaissent pas dans le navigateur.",
            "Verifiez si un navigateur par defaut est configure. Essayez alternativement "
            "l'export PDF. Assurez-vous que le fichier IssueTimes a ete charge correctement "
            "(verifiez le journal)."
        ),
        (
            "L'export PDF prend tres longtemps ou echoue.",
            "Le rendu des diagrammes en PDF necessite le package Kaleido. Si celui-ci n'a "
            "pas encore ete configure, contactez votre correspondant technique."
        ),
        (
            "Le journal affiche 'Stage only in IssueTimes' ou 'Stage only in CFD'.",
            "Les colonnes d'etapes dans IssueTimes.xlsx et CFD.xlsx ne correspondent pas. "
            "Il s'agit d'un avertissement qui n'arrete pas l'analyse, mais indique que les "
            "fichiers proviennent de versions de workflow differentes."
        ),
        (
            "Comment analyser uniquement un projet specifique ?",
            "Saisissez la cle de projet souhaitee dans le champ 'Projets' (ex. ARTA). "
            "Separaz plusieurs projets par une virgule. Alternativement : utilisez le bouton "
            "de selection pour une liste de tous les projets disponibles."
        ),
        (
            "Le Cumulative Flow Diagram n'apparait pas.",
            "La metrique CFD requiert un fichier CFD.xlsx. Chargez-le dans le champ "
            "'CFD (optionnel)'."
        ),
        (
            "Process Flow affiche 'No transition data available'.",
            "La metrique Process Flow requiert un fichier Transitions.xlsx de transform_data. "
            "Chargez-le dans le champ 'Transitions (optionnel)'. Assurez-vous que le fichier "
            "provient du meme export que IssueTimes.xlsx."
        ),
        (
            "Quelle est la difference entre les intervalles PI et les trimestres ?",
            "Par defaut, les trimestres calendaires (Q1-Q4) sont utilises comme intervalles "
            "de temps. Avec un fichier de configuration PI, vous pouvez definir vos propres "
            "intervalles correspondant a vos PIs reels -- par exemple si votre PI commence "
            "le 6 janvier au lieu du 1er janvier."
        ),
        (
            "Comment enregistrer mes parametres ?",
            "Utilisez le menu 'Modeles' -> 'Enregistrer...' pour enregistrer tous les "
            "parametres actuels dans un fichier JSON. La prochaine fois : 'Modeles' -> "
            "'Charger...'. Les parametres d'exclusion peuvent egalement etre stockes "
            "definitivement sous 'Modeles' -> 'Enregistrer les exclusions par defaut'."
        ),
        (
            "Un ticket apparait dans les metriques alors qu'il n'a jamais vraiment ete traite.",
            "Cela se produit lorsqu'un ticket a ete passe manuellement en revue dans toutes "
            "les etapes du workflow en quelques secondes -- sans aucun travail de "
            "developpement reel. Activez la case 'Exclure les tickets zero-day' sous "
            "'Exclusions' dans la GUI (seuil par ex. 5 minutes). Le ticket est alors "
            "completement supprime de toutes les metriques et documente dans un fichier "
            "Excel separe."
        ),
        (
            "Puis-je presenter les resultats sans ordinateur ?",
            "Oui : exportez d'abord un rapport PDF. Le fichier PDF contient tous les "
            "diagrammes et peut etre ouvert sur n'importe quel appareil. Pour les "
            "presentations interactives, la vue navigateur est recommandee."
        ),
    ]
    for q, a in faqs:
        story.append(H3("Q : " + q, st))
        story.append(P("R : " + a, st))
        story.append(SP(4))

    # =========================================================================
    # 8. Glossaire
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("8  Glossaire", st))
    story.append(tbl(
        ["Terme", "Explication"],
        [
            ["Closed Date",    "La date a laquelle un ticket a ete termine."],
            ["Cycle Time",     "Terme alternatif pour Flow Time (terminologie Global)."],
            ["First Date",     "Date du premier travail actif sur un ticket."],
            ["Flow Load",      "Nombre de tickets actuellement en cours (terme SAFe)."],
            ["Flow Time",      "Cycle time du premier travail jusqu'a la completion."],
            ["Flow Velocity",  "Nombre de tickets termines par periode de temps (terme SAFe)."],
            ["Issue",          "Un ticket dans le gestionnaire de tickets (ex. une carte Jira)."],
            ["Issue type",     "Categorie d'un ticket, ex. Feature, Bug, Story, Task."],
            ["IssueTimes",     "Le fichier Excel avec tous les tickets produit par transform_data."],
            ["JSON",           "Format texte simple pour les fichiers de configuration."],
            ["LOESS",          "Methode de lissage statistique pour les lignes de tendance."],
            ["P85 / P95",      "85e / 95e percentile des cycle times."],
            ["PI",             "Program Increment -- une periode de planification et de livraison fixe."],
            ["Process Flow: Transitions", "Graphe oriente de toutes les transitions de statut (base sur la frequence). Montre les chemins principaux, les retours et les boucles dans le workflow."],
            ["Process Flow: Time",        "Graphe oriente de toutes les transitions de statut (base sur le temps). La largeur des noeuds et les etiquettes d'aretes montrent le temps de sejour median par etape."],
            ["Resolution",     "Type de resolution d'un ticket, ex. 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework -- un framework pour la mise a l'echelle agile."],
            ["Stage",          "Une etape dans le workflow, ex. Analyse, Implementation, Done."],
            ["Template",       "Fichier de configuration enregistre avec tous les parametres."],
            ["Throughput",     "Terme alternatif pour Flow Velocity (terminologie Global)."],
            ["Transitions",    "Enregistrement de chaque changement de statut par ticket. Exporte par transform_data sous Transitions.xlsx."],
            ["WIP",            "Work in Progress -- tickets actuellement en cours de traitement."],
            ["Zero-day issue", "Un ticket dont le cycle time (First to Closed Date) est si court "
                               "qu'il ne represente pas un temps de traitement reel. Generalement cause "
                               "par un passage manuel dans le workflow. Peut etre supprime de toutes "
                               "les metriques via un filtre de seuil."],
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
    """Generate build_reports user manual PDFs in all 5 languages."""
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
        _build_doc(
            OUTPUT_RO, LANG_RO, content_ro,
            title="build_reports Manual de Utilizator",
            subject="Metrici de flux pentru echipe agile",
            images=images,
        )
        _build_doc(
            OUTPUT_PT, LANG_PT, content_pt,
            title="build_reports Manual do Utilizador",
            subject="Metricas de fluxo para equipas ageis",
            images=images,
        )
        _build_doc(
            OUTPUT_FR, LANG_FR, content_fr,
            title="build_reports Manuel d'utilisation",
            subject="Metriques de flux pour equipes agiles",
            images=images,
        )
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
